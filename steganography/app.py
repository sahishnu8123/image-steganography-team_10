from flask import Flask, render_template, request, send_file
from PIL import Image
import os
import uuid

app = Flask(__name__)

# -------- CONFIG (VERY IMPORTANT FOR 512MB) --------
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # 4 MB max upload

END_MARKER = "|||END|||"

# -------- IMAGE OPTIMIZATION --------
def optimize_image(path):
    img = Image.open(path)
    img = img.convert("RGB")
    img.thumbnail((800, 800))   # LIMIT SIZE → LOW RAM

    opt_path = path.replace(".", "_opt.")
    img.save(opt_path, "PNG")
    img.close()
    return opt_path

# -------- JPEG → PNG INTERNAL CONVERSION --------
def convert_to_png(path):
    img = Image.open(path)
    png_path = path.replace(".", "_png.")
    img.convert("RGB").save(png_path, "PNG")
    img.close()
    return png_path

# -------- TEXT TO BINARY --------
def text_to_binary(text):
    full = text + END_MARKER
    return ''.join(format(ord(c), '08b') for c in full)

# -------- ENCODE IMAGE (LOW MEMORY) --------
def encode_image(image_path, secret_text, output_format):
    img = Image.open(image_path)
    pixels = img.load()

    binary = text_to_binary(secret_text)
    width, height = img.size
    idx = 0

    for y in range(height):
        for x in range(width):
            if idx >= len(binary):
                break

            r, g, b = pixels[x, y]

            if idx < len(binary):
                r = (r & ~1) | int(binary[idx]); idx += 1
            if idx < len(binary):
                g = (g & ~1) | int(binary[idx]); idx += 1
            if idx < len(binary):
                b = (b & ~1) | int(binary[idx]); idx += 1

            pixels[x, y] = (r, g, b)

        if idx >= len(binary):
            break

    output_name = f"encoded_{uuid.uuid4().hex}"

    if output_format == "jpeg":
        out_path = os.path.join(UPLOAD_FOLDER, output_name + ".jpg")
        img.save(out_path, "JPEG", quality=90)
    else:
        out_path = os.path.join(UPLOAD_FOLDER, output_name + ".png")
        img.save(out_path, "PNG")

    img.close()
    return out_path

# -------- FAST & SAFE DECODE --------
def decode_image(image_path):
    img = Image.open(image_path)
    pixels = img.load()
    width, height = img.size

    binary = ""
    message = ""

    for y in range(height):
        for x in range(width):
            for value in pixels[x, y]:
                binary += str(value & 1)

                if len(binary) == 8:
                    char = chr(int(binary, 2))
                    message += char
                    binary = ""

                    if END_MARKER in message:
                        img.close()
                        return message.replace(END_MARKER, "")

    img.close()
    return "No hidden message found"

# -------- CLEAN TEMP FILES --------
def safe_delete(*paths):
    for p in paths:
        try:
            os.remove(p)
        except:
            pass

# -------- HOME / ENCODE --------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        image = request.files["image"]
        message = request.form["message"]
        output_format = request.form["format"]

        raw_path = os.path.join(UPLOAD_FOLDER, image.filename)
        image.save(raw_path)

        # JPEG → PNG (internal)
        if raw_path.lower().endswith((".jpg", ".jpeg")):
            raw_path = convert_to_png(raw_path)

        # Resize & optimize
        optimized_path = optimize_image(raw_path)

        output = encode_image(optimized_path, message, output_format)

        safe_delete(raw_path, optimized_path)

        return send_file(output, as_attachment=True)

    return render_template("index.html")

# -------- DECODE --------
@app.route("/decode", methods=["GET", "POST"])
def decode():
    secret_message = ""

    if request.method == "POST":
        image = request.files["image"]
        raw_path = os.path.join(UPLOAD_FOLDER, image.filename)
        image.save(raw_path)

        if raw_path.lower().endswith((".jpg", ".jpeg")):
            raw_path = convert_to_png(raw_path)

        optimized_path = optimize_image(raw_path)

        secret_message = decode_image(optimized_path)

        safe_delete(raw_path, optimized_path)

    return render_template("decode.html", message=secret_message)

# -------- RUN --------
if __name__ == "__main__":
    app.run()

  

