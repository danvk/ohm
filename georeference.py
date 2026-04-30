import base64

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
image_path = "brooklyn-sanborn.958x1395-fs8.png"

# Getting the Base64 string
base64_image = encode_image(image_path)

PROMPT = """Your task is to find the (x, y) coordinates and street names of the intersections on a map.

- You'll be given an image of a street map. The street names are labeled and the edges of the streets are delineated with black lines. The street names may be rotated. Streets may be vertical, horizontal, or diagonal, and they may bend. There will be other text on the map that is unrelated to streets.
- You'll also be given a list of known intersections that might appear in the image. Only look for these intersections. The street names may not match exactly due to abbreviations, e.g. "St" vs. "Street", "Ave" vs. "Avenue" and "Pl" vs. "Place". Not all intersections in the list will appear in the image. Not all intersections in the image will appear in the list. Only include intersections that are in both.
- Only include intersections that you can identify with high confidence. It is better to include fewer intersections that you're more confident of than more intersections that you're less sure about.

Your output should be a JSON object matching the following TypeScript interface:

interface Response {
  width: number;  // image width, in pixels
  height: number;  // image height, in pixels
  points: Array<{
    x: number;  // x-coordinate of the center of the intersection
    y: number;  // y-coordinate of the center of the intersection
    // fields from the list of streets:
    street1: string;
    street2: string;
  }>;
}

The list of known intersections follows:

----
street1,street2
Atlantic Avenue,Columbia Street
Atlantic Avenue,Hicks Street
Atlantic Avenue,Henry Street
Atlantic Avenue,Clinton Street
State Street,Columbia Place
State Street,Willow Place
State Street,Hicks Street
State Street,Garden Place
State Street,Henry Street
State Street,Sidney Place
State Street,Clinton Street
Joralemon Street,Columbia Place
Joralemon Street,Willow Place
Joralemon Street,Hicks Street
Joralemon Street,Garden Place
Joralemon Street,Henry Street
Joralemon Street,Sidney Place
Joralemon Street,Clinton Street
Aitken Place,Sidney Place
Aitken Place,Clinton Street
"""


response = client.responses.create(
    model="gpt-5.5",
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": PROMPT},
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
