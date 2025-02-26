"""
File: _blog.py

Blog class for ROCmBlogs package.
"""

import io
import os
import pathlib  
from datetime import datetime
import re
import shutil

from PIL import Image


class Blog:
    def __init__(self, file_path, metadata, image=None):
        self.file_path = file_path
        self.metadata = metadata
        self.image = image
        self.image_paths = []
        self.word_count = 0

        # Dynamically set attributes based on metadata

        for key, value in metadata.items():
            setattr(self, key, value)
        # Ensure the 'date' field exists

        if "date" in metadata:
            self.date = self.parse_date(metadata["date"])
        else:
            self.date = None

    def set_word_count(self, word_count) -> None:
        """Set the word count for the blog."""
        
        self.word_count = word_count

    def set_file_path(self, file_path) -> None:
        """Set the file path for the blog."""

        self.file_path = file_path

    def normalize_date_string(self, date_str) -> str:
        """Normalize the date string."""

        # do not remove !important

        date_str = date_str.replace("Sept", "Sep")

        return date_str

    def load_image_to_memory(self, image_path, format="PNG") -> None:
        """Load an image into memory."""

        try:
            with Image.open(image_path) as img:
                buffer = io.BytesIO()

                img.save(buffer, format=format)

                buffer.seek(0)

                self.image = buffer.getvalue()

                print(f"Image loaded into memory; size: {len(self.image)} bytes.")
        except Exception as error:
            print(f"Error loading image to memory: {error}")

    def save_image(self, output_path) -> None:
        """Save the image to disk."""

        if self.image is None:
            print("No image data available in memory to save.")

            return
        try:
            with open(output_path, "wb", encoding="utf-8") as file:
                file.write(self.image)

                print(f"Image saved to disk at: {output_path}")
        except Exception as error:
            print(f"Error saving image to disk: {error}")

    def save_image_path(self, image_path) -> None:
        """Save the image path for later use."""

        self.image_paths.append(image_path)

    def parse_date(self, date_str) -> datetime | None:
        """Parse the date string into a datetime object."""

        # Normalize the date string

        date_str = self.normalize_date_string(date_str)

        # Define possible date formats, including string-based months

        date_formats = [
            "%d-%m-%Y",  # e.g. 8-08-2024
            "%d/%m/%Y",  # e.g. 8/08/2024
            "%d-%B-%Y",  # e.g. 8-August-2024
            "%d-%b-%Y",  # e.g. 8-Aug-2024
            "%d %B %Y",  # e.g. 8 August 2024
            "%d %b %Y",  # e.g. 8 Aug 2024
            "%d %B, %Y",  # e.g. 8 August, 2024
            "%d %b, %Y",  # e.g. 8 Aug, 2024
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        print(f"Invalid date format in {self.file_path}: {date_str}")

        return None

    def grab_href(self) -> str:
        """Grab the href for the blog."""

        href = self.file_path.replace(".md", ".html")

        href = href.replace("\\", "/")

        return href
    
    def grab_authors(self, authors_list: list) -> str:
        """
        Generate HTML links for authors.
        
        Args:
            authors_list: A list of author names.
            
        Returns:
            HTML links for the authors.
        """
        # Process an author which may be a list
        def proc(author):
            return " ".join(author) if isinstance(author, list) else author

        return (
            ", ".join(
                f'<a href="https://rocm.blogs.amd.com/blog/authors/{proc(author).strip().replace(" ", "-").lower()}.html">{proc(author).strip()}</a>'
                for author in authors_list
            )
            or ""
        )

    def optimize_image(self, image) -> None:
        """Optimize the image."""

        try:
            with Image.open(image) as img:
                before_size = os.path.getsize(image)

                original_width, original_height = img.size

                max_width, max_height = (1280, 420)
                scaling_factor = min(
                    max_width / original_width, max_height / original_height
                )

                new_width = int(original_width * scaling_factor)
                new_height = int(original_height * scaling_factor)

                img = img.resize((new_width, new_height), resample=Image.LANCZOS)

                img.save(image, optimize=True, quality=80)

                after_size = os.path.getsize(image)

                print(
                    f"Before optimization: {before_size} - After optimization: {after_size} - \
                        Total reduction of {((before_size - after_size) / before_size) * 100} percent"
                )

                with open("optimize.txt", "a", encoding="utf-8") as f:
                    f.write(
                        f"Before optimization: {before_size} - After optimization: {after_size} - \
                            Total reduction of {((before_size - after_size) / before_size) * 100} percent\n on {image}\n"
                    )
        except Exception as error:
            print(f"Error optimizing image {image}: {error}")
    
    def grab_image(self, rocmblogs) -> pathlib.Path:
        """Grab the image for the blog"""

        print(f"Processing image for blog: {self.blog_title if hasattr(self, 'blog_title') else 'Unknown'}")
        print(f"Blog file path: {self.file_path}")
        print(f"Blogs directory: {rocmblogs.blogs_directory}")
        
        # Get the thumbnail from metadata
        image = getattr(self, "thumbnail", None)
        print(f"Original thumbnail value: {image}")

        # Print all attributes of the blog object to help diagnose issues
        print("Blog attributes:")
        for attr_name in dir(self):
            if not attr_name.startswith('__') and not callable(getattr(self, attr_name)):
                attr_value = getattr(self, attr_name)
                if not isinstance(attr_value, (dict, list)) or attr_name == 'thumbnail':
                    print(f"  {attr_name}: {attr_value}")

        full_image_path = None

        if not image:
            print("No thumbnail specified in metadata, using generic.jpg")
            self.image = "generic.jpg"
            return "./images/generic.jpg"

        # Handle different image path formats
        # If the image path contains "/images/" or "\images\", extract just the filename
        if "/images/" in image or "\\images\\" in image:
            image = os.path.basename(image)
            print(f"Extracted image filename: {image}")

        # Try to find the image in various locations
        # 1. First check if the image path is absolute and exists
        if os.path.isabs(image) and os.path.exists(image):
            full_image_path = pathlib.Path(image)
            print(f"Found image at absolute path: {full_image_path}")
        else:
            # 2. Check relative to the blog file
            possible_paths = [
                # In the same directory as the blog file
                pathlib.Path(self.file_path).parent / image,
                # In an 'images' subdirectory of the blog file's directory
                pathlib.Path(self.file_path).parent / "images" / image,
                # In the parent directory's 'images' folder
                pathlib.Path(self.file_path).parent.parent / "images" / image,
                # In the root 'images' folder (3 levels up)
                pathlib.Path(self.file_path).parent.parent.parent / "images" / image,
                # In the blogs directory's 'images' folder
                pathlib.Path(rocmblogs.blogs_directory) / "images" / image,
                # Try with lowercase filename (in case of case sensitivity issues)
                pathlib.Path(rocmblogs.blogs_directory) / "images" / image.lower(),
            ]
            
            print("Checking possible image paths:")
            for path in possible_paths:
                print(f"  Checking: {path}")
                if path.exists():
                    full_image_path = path
                    print(f"  Found image at: {full_image_path}")
                    break

            # If still not found, try listing all images in the blogs/images directory to see what's available
            if not full_image_path:
                images_dir = pathlib.Path(rocmblogs.blogs_directory) / "images"
                if images_dir.exists():
                    print(f"Listing all images in {images_dir}:")
                    for img_file in images_dir.glob("*"):
                        print(f"  Available image: {img_file.name}")
                    
                    # Try to find a partial match
                    print("Looking for partial matches:")
                    image_base = os.path.splitext(image)[0]
                    for img_file in images_dir.glob("*"):
                        if image_base.lower() in img_file.name.lower():
                            print(f"  Found partial match: {img_file}")
                            full_image_path = img_file
                            break

        if not full_image_path:
            print(f"Image not found: {image}")
            self.image = "generic.jpg"
            return "./images/generic.jpg"

        # For grid items, we want to use the original image path
        # This will be properly handled by Sphinx during the build process
        # and copied to _build/html/_images
        
        # Return the path relative to the blogs directory
        # This is what Sphinx expects for image references
        relative_path = os.path.relpath(str(full_image_path), str(rocmblogs.blogs_directory))
        
        # Ensure the path uses forward slashes for consistency
        relative_path = relative_path.replace("\\", "/")
        
        # If the path doesn't start with "./", add it
        if not relative_path.startswith("./"):
            relative_path = "./" + relative_path
            
        print(f"Using image at relative path: {relative_path}")
        
        # Save the image name (without path) for use in blog pages
        image_name = os.path.basename(str(full_image_path))
        self.save_image_path(image_name)
        
        return relative_path

    def __repr__(self) -> str:
        """Return a string representation of the class."""
        
        return f"Blog(file_path='{self.file_path}', metadata={self.metadata})"
