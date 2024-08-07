import io
from pathlib import Path
import shutil

from PIL import Image
from rembg import remove


# Function to find the bounding box of the car and the size of the bounding box
def find_car_bounding_box(img: Image):
    pixels = img.load()
    width, height = img.size
    left, top, right, bottom = width, height, -1, -1

    for x in range(width):
        for y in range(height):
            # Considering non-black pixels as part of the car
            if pixels[x, y] != (0, 0, 0):
                left = min(left, x)
                right = max(right, x)
                top = min(top, y)
                bottom = max(bottom, y)

    # Return the bounding box coordinates and its size
    return (left, top, right, bottom), (right - left, bottom - top)


# Function to center and resize the car in the new image
def resize_and_center_car(
    img: Image, car_size: tuple[int, int], new_dimensions: tuple[int, int]
):
    # Calculate the size ratio
    ratio = min(new_dimensions[0] / car_size[0], new_dimensions[1] / car_size[1])
    new_car_size = (int(car_size[0] * ratio), int(car_size[1] * ratio))

    # Resize the car
    img = img.resize(new_car_size, Image.LANCZOS)

    # Create a new image with black background and new dimensions
    new_img = Image.new("RGB", new_dimensions, (0, 0, 0))

    # Calculate the position to center the car
    position = (
        (new_dimensions[0] - new_car_size[0]) // 2,
        (new_dimensions[1] - new_car_size[1]) // 2,
    )

    # Paste the car image onto the new image, centered
    new_img.paste(img, position)

    return new_img


# Define the directory paths
DATASET_PATH = Path("data")
PREPROCESSED_DATASET_PATH = Path("preprocessed data")
LOG_PATH = Path("processed_images.log")

# Read the log file to find out which images have been processed
if LOG_PATH.exists():
    with open(LOG_PATH, "r") as log_file:
        processed_images = set(log_file.read().splitlines())
else:
    processed_images: set[str] = set()

PREPROCESSED_DATASET_PATH.mkdir(parents=True, exist_ok=True)

# Process the images in the dataset
with open(LOG_PATH, "a") as log_file:
    for img_path in DATASET_PATH.rglob("*.jpg"):
        if img_path.name in processed_images:
            continue

        with open(img_path, "rb") as file:
            input_data = file.read()

        # Remove the background
        output_data = remove(input_data)

        # Convert to PIL image for further processing and convert to RGB
        img = Image.open(io.BytesIO(output_data)).convert("RGB")

        # Find the car's bounding box and size
        (left, top, right, bottom), car_size = find_car_bounding_box(img)

        # Crop the car out of the image using the bounding box
        car_img = img.crop((left, top, right, bottom))

        # Resize and center the car in the new image
        # final_img = resize_and_center_car(car_img, car_size, (224, 128))
        final_img = resize_and_center_car(car_img, car_size, (448, 256))

        # Create the directory for the preprocessed image if it doesn't exist
        new_parent_dir = PREPROCESSED_DATASET_PATH / img_path.parent.name
        new_parent_dir.mkdir(parents=True, exist_ok=True)

        # Save the processed image
        final_img_path = new_parent_dir / img_path.name
        final_img.save(final_img_path, "JPEG")

        # Update the log file
        log_file.write(f"{img_path.name}\n")
        processed_images.add(img_path.name)
