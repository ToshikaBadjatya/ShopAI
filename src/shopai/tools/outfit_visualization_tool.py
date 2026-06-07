"""
Outfit Visualization Tool
Generates a 1024x1024 outfit visualization image using Gemini 2.5 Flash Image.

Workflow:
  1. Accepts the first product link from the recommendation agent output,
     plus the user's gender, height, and body_type.
  2. Builds a detailed text prompt that describes:
       - A realistic body-type/height/gender model silhouette
       - The outfit sourced from the product link description
  3. Calls the Gemini 2.5 Flash image-generation model.
  4. Saves the resulting PNG to src/shopai/output/outfit_visualization.png.
  5. Returns the saved file path so the visualize agent can embed it in
     shopping_guide.md.
"""

import base64
import os
import re
from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Output directory — resolves to  src/shopai/output/
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "outfit_visualization.png"


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------
class OutfitVisualizationInput(BaseModel):
    """Input schema for the outfit visualization tool."""

    product_url: str = Field(
        ...,
        description=(
            "The first product URL returned by the recommendation agent "
            "(e.g. 'https://www.amazon.in/dp/XXXXXXXXXX').  "
            "Used to derive the outfit name / description for the image prompt."
        ),
    )
    outfit_description: str = Field(
        ...,
        description=(
            "Short plain-text description of the full outfit to visualise, "
            "e.g. 'flutter-sleeve tiered midi dress, strappy flat sandals, "
            "wide-brimmed straw hat, straw crossbody bag, square sunglasses'."
        ),
    )
    gender: str = Field(
        ...,
        description="Gender of the model, e.g. 'female', 'male', 'non-binary'.",
    )
    height: str = Field(
        ...,
        description="Height of the model, e.g. '5\\'10\"' or '178 cm'.",
    )
    body_type: str = Field(
        ...,
        description=(
            "Body type of the model, e.g. 'skinny', 'slim', 'athletic', "
            "'curvy', 'plus-size', 'petite'."
        ),
    )


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------
class OutfitVisualizationTool(BaseTool):
    name: str = "outfit_visualizer"
    description: str = (
        "Generates a 1024x1024 outfit visualization image using Gemini 2.5 Flash Image. "
        "Pass the first product URL from the recommendation agent together with "
        "the user's gender, height, and body type. "
        "The tool builds a body-type-appropriate model, dresses it in the selected "
        "outfit, and saves the image to src/shopai/output/outfit_visualization.png. "
        "Returns the saved file path for embedding in the shopping guide."
    )
    args_schema: Type[BaseModel] = OutfitVisualizationInput

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        product_url: str,
        outfit_description: str,
        gender: str,
        height: str,
        body_type: str,
    ) -> str:
        """Construct a detailed image-generation prompt."""
        # Derive a human-readable product hint from the URL slug
        slug = product_url.rstrip("/").split("/")[-1]
        slug_hint = re.sub(r"[^a-zA-Z0-9 ]", " ", slug).strip()

        prompt = (
            f"Full-body fashion photograph of a single {gender} model. "
            f"The model is {height} tall with a {body_type} body type. "
            f"The model is wearing: {outfit_description}. "
            f"The outfit style is inspired by: {slug_hint}. "
            "The model is standing in a well-lit, neutral studio background. "
            "The image is styled like a professional fashion editorial — "
            "sharp focus, natural lighting, clean white background. "
            "Show the complete outfit from head to toe. "
            "Do NOT include any text, watermarks, or logos in the image. "
            "Square 1:1 aspect ratio."
        )
        return prompt

    def _save_image(self, image_bytes: bytes) -> Path:
        """Ensure output directory exists and write the PNG."""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_bytes(image_bytes)
        return OUTPUT_FILE

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def _run(
        self,
        product_url: str,
        outfit_description: str,
        gender: str,
        height: str,
        body_type: str,
    ) -> str:
        try:
            from google import genai  # type: ignore[import]
            from google.genai import types as genai_types  # type: ignore[import]
        except ImportError:
            return (
                "Error: 'google-genai' package is not installed. "
                "Run: uv add google-genai"
            )

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return (
                "Error: No Gemini API key found. "
                "Set GEMINI_API_KEY or GOOGLE_API_KEY in your .env file."
            )

        prompt = self._build_prompt(
            product_url, outfit_description, gender, height, body_type
        )

        try:
            client = genai.Client(api_key=api_key)

            response = client.models.generate_content(
                model="gemini-2.0-flash-preview-image-generation",
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    image_generation_config=genai_types.ImageGenerationConfig(
                        number_of_images=1,
                        output_mime_type="image/png",
                        aspect_ratio="1:1",
                    ),
                ),
            )

            # Extract image bytes from response parts
            image_bytes: bytes | None = None
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    image_bytes = part.inline_data.data
                    # data may already be bytes or base64-encoded string
                    if isinstance(image_bytes, str):
                        image_bytes = base64.b64decode(image_bytes)
                    break

            if not image_bytes:
                return (
                    "Error: Gemini returned a response but no image data was found. "
                    f"Raw response text: {response.text[:300] if response.text else 'empty'}"
                )

            saved_path = self._save_image(image_bytes)
            return (
                f"Outfit visualization saved to: {saved_path}\n"
                f"Embed in markdown with: ![Outfit Visualization]({saved_path})\n"
                f"Prompt used: {prompt[:200]}..."
            )

        except Exception as exc:  # noqa: BLE001
            return f"Error generating outfit visualization: {exc}"
