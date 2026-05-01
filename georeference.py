import base64
import sys

from dotenv import find_dotenv, load_dotenv
from openai import OpenAI

dotenv_path = find_dotenv(usecwd=True)
load_dotenv(dotenv_path=dotenv_path)
client = OpenAI()


# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


# Path to your image
# image_path = "brooklyn-sanborn.958x1395-fs8.png"
# image_path = "/Users/danvk/Documents/ohm/brooklyn-sanborn-11s-fs8.png"
(image_path,) = sys.argv[1:]

# Getting the Base64 string
base64_image = encode_image(image_path)

PROMPT = """Your task is to find the (x, y) coordinates and street names of the intersections on a map.

- You'll be given an image of a street map. The street names are labeled and the edges of the streets are delineated with black lines. The street names may be rotated. Streets may be vertical, horizontal, or diagonal, and they may bend. There will be other text on the map that is unrelated to streets.
- You'll also be given a list of known intersections that might appear in the image. Only look for these intersections. The street names may not match exactly due to abbreviations, e.g. "St" vs. "Street", "Ave" vs. "Avenue" and "Pl" vs. "Place". Not all intersections in the list will appear in the image. Not all intersections in the image will appear in the list. Only include intersections that are in both.
- Only include intersections that you can identify with high confidence. It is better to include fewer intersections that you're more confident of than more intersections that you're less sure about.
- Do not resize, pad or crop the image. Give (x, y) coordinates for the input image.

Your output should be a JSON object matching the following TypeScript interface:

interface Response {
  width: number;  // input image width, in pixels
  height: number;  // input image height, in pixels
  points: Array<{
    x: number;  // x-coordinate of the center of the intersection
    y: number;  // y-coordinate of the center of the intersection
    // fields from the list of streets:
    street1: string;
    street2: string;
  }>;
}

The list of known intersections is provided as a separate CSV input.
"""

INTERSECTIONS_CSV = open("streets-rag.csv").read()


response = client.responses.create(
    model="gpt-5.5",
    # model="gpt-5.4",
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": PROMPT},
                {"type": "input_text", "text": INTERSECTIONS_CSV},
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{base64_image}",
                    "detail": "original",
                },
            ],
        }
    ],
    text={"format": {"type": "json_object"}},
)

print(response.output_text)
