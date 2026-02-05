from flask import Flask, render_template, request, send_file
from PIL import Image
import os
import uuid

app = Flask(__name__)

# ---------- CONFIG ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # 4 MB
END_MARKER = "|||END|||"


# ---------- HELPERS ----------
def optimize_image(path):
    img = Image.open(path)
    img = img.convert("RGB")
    img.thumbnail((800, 800))
    img.save(path, "PNG")
    img.close()
    return path


def convert_to_png(path):
    img = Image.open(path)
    new_path = path.rsplit(".", 1)[0] + "_png.png"
    img.convert("RGB").save(new_path, "PNG")
    img.close()
    return new_path


def text_to_binary(text):
    return ''.join(format(ord(c), '08b') for c in (text + END_MARKER))


# ---------- ENCODE ----------
def encode_image(image_path, message, output_format):
    img = Image.open(image_path)
    pixels = img.load()
    width, height = img.size

    binary = text_to_binary(message)
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

    name = f"encoded_{uuid.uuid4().hex}"
    if output_format == "jpeg":
        out = os.path.join(UPLOAD_FOLDER, name + ".jpg")
        img.save(out, "JPEG", quality=90)
    else:
        out = os.path.join(UPLOAD_FOLDER, name + ".png")
        img.save(out, "PNG")

    img.close()
    return out


# ---------- DECODE ----------
def decode_image(path):
    img = Image.open(path)
    pixels = img.load()
    width, height = img.size

    binary = ""
    message = ""

    for y in range(height):
        for x in range(width):
            for v in pixels[x, y]:
                binary += str(v & 1)
                if len(binary) == 8:
                    ch = chr(int(binary, 2))
                    message += ch
                    binary = ""
                    if END_MARKER in message:
                        img.close()
                        return message.replace(END_MARKER, "")

    img.close()
    return "No hidden message found"


# ---------- ROUTES ----------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        image = request.files.get("image")
        message = request.form.get("message")
        fmt = request.form.get("format", "png")

        if not image or not message:
            return "Invalid input", 400

        raw_path = os.path.join(UPLOAD_FOLDER, image.filename)
        image.save(raw_path)

        if raw_path.lower().endswith((".jpg", ".jpeg")):
            raw_path = convert_to_png(raw_path)

        optimize_image(raw_path)
        output = encode_image(raw_path, message, fmt)

        return send_file(output, as_attachment=True)

    return render_template("index.html")


@app.route("/decode", methods=["GET", "POST"])
def decode():
    message = ""

    if request.method == "POST":
        image = request.files.get("image")
        if not image:
            return "No image uploaded", 400

        raw_path = os.path.join(UPLOAD_FOLDER, image.filename)
        image.save(raw_path)

        if raw_path.lower().endswith((".jpg", ".jpeg")):
            raw_path = convert_to_png(raw_path)

        optimize_image(raw_path)
        message = decode_image(raw_path)

    return render_template("decode.html", message=message)


# ---------- START ----------
if __name__ == "__main__":
    app.run()

  


