from flask import Flask, render_template, request, send_file
from PIL import Image
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

END_MARKER = "|||END|||"


# ---------- HELPER: CONVERT ANY IMAGE TO PNG ----------
def convert_to_png(image_path):
    img = Image.open(image_path)
    png_path = image_path.rsplit(".", 1)[0] + "_internal.png"
    img.convert("RGB").save(png_path, "PNG")
    return png_path


# ---------- TEXT TO BINARY ----------
def text_to_binary(text):
    full_text = text + END_MARKER
    return ''.join(format(ord(c), '08b') for c in full_text)


# ---------- ENCODE IMAGE ----------
def encode_image(image_path, secret_text, output_format):
    img = Image.open(image_path)
    pixels = list(img.getdata())

    binary = text_to_binary(secret_text)
    index = 0
    new_pixels = []

    for pixel in pixels:
        r, g, b = pixel

        if index < len(binary):
            r = (r & ~1) | int(binary[index])
            index += 1
        if index < len(binary):
            g = (g & ~1) | int(binary[index])
            index += 1
        if index < len(binary):
            b = (b & ~1) | int(binary[index])
            index += 1

        new_pixels.append((r, g, b))

    img.putdata(new_pixels)

    if output_format == "jpeg":
        output_path = os.path.join(UPLOAD_FOLDER, "encoded.jpg")
        img.convert("RGB").save(output_path, "JPEG")
    else:
        output_path = os.path.join(UPLOAD_FOLDER, "encoded.png")
        img.save(output_path, "PNG")

    return output_path


# ---------- FAST DECODE IMAGE ----------
def decode_image(image_path):
    img = Image.open(image_path)
    pixels = img.getdata()

    binary = ""
    message = ""

    for pixel in pixels:
        for value in pixel:
            binary += str(value & 1)

            if len(binary) == 8:
                char = chr(int(binary, 2))
                message += char
                binary = ""

                if END_MARKER in message:
                    return message.replace(END_MARKER, "")

    return "No hidden message found"


# ---------- ENCODE ROUTE ----------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        image = request.files["image"]
        message = request.form["message"]
        output_format = request.form["format"]

        image_path = os.path.join(UPLOAD_FOLDER, image.filename)
        image.save(image_path)

        # AUTO-CONVERT JPEG → PNG (INTERNAL)
        if image.filename.lower().endswith((".jpg", ".jpeg")):
            image_path = convert_to_png(image_path)

        output = encode_image(image_path, message, output_format)
        return send_file(output, as_attachment=True)

    return render_template("index.html")


# ---------- DECODE ROUTE ----------
@app.route("/decode", methods=["GET", "POST"])
def decode():
    secret_message = ""

    if request.method == "POST":
        image = request.files["image"]
        image_path = os.path.join(UPLOAD_FOLDER, image.filename)
        image.save(image_path)

        # AUTO-CONVERT JPEG → PNG (INTERNAL)
        if image.filename.lower().endswith((".jpg", ".jpeg")):
            image_path = convert_to_png(image_path)

        secret_message = decode_image(image_path)

    return render_template("decode.html", message=secret_message)


# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
