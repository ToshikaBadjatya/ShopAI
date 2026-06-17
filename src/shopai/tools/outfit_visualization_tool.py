"""
Outfit Visualization Tool
Generates an outfit visualization image using the configured IMAGE_MODEL via the
Hugging Face Inference API (other agents keep using OpenRouter).
Inputs: outfit_description and body_type, height,from user object only.
"""

import os
import uuid
from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

OUTPUT_DIR = Path(__file__).parent.parent / "output"


class OutfitVisualizationInput(BaseModel):
    outfit_description: str = Field(
        ...,
        description=(
            "Plain-text description of the full outfit to visualise, "
            "e.g. 'flutter-sleeve midi dress, strappy sandals, straw hat'."
        ),
    )
    body_type: str = Field(
        ...,
        description="Body type of the model, e.g. 'slim', 'athletic', 'curvy', 'plus-size'.",
    )
    height: str = Field(
        default="",
        description="Height of the model, e.g. '5\\'6\"' or '5\\'0\" - 5\\'3\"'.",
    )


class OutfitVisualizationTool(BaseTool):
    name: str = "outfit_visualizer"
    description: str = (
        "Generates an outfit visualization image using the configured image model. "
        "Pass the outfit description and body type. "
        "Returns the saved file path for embedding in the shopping guide."
    )
    args_schema: Type[BaseModel] = OutfitVisualizationInput

    def _build_prompt(self, outfit_description: str, body_type: str, height: str = "") -> str:
        height_clause = f" approximately {height} tall" if height else ""
        return (
            f"Full-body fashion photograph of a single model with a {body_type} body type{height_clause}. "
            f"The model is wearing: {outfit_description}. "
            "Standing in a well-lit, neutral studio with clean white background. "
            "Professional fashion editorial style — sharp focus, natural lighting. "
            "Show the complete outfit from head to toe. "
            "No text, watermarks, or logos. Square 1:1 aspect ratio."
        )

    def _run(self, outfit_description: str, body_type: str, height: str = "") -> str:
        try:
            from huggingface_hub import InferenceClient
        except ImportError:
            return "Error: 'huggingface_hub' package is not installed. Run: uv add huggingface_hub"

        api_key = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY")
        if not api_key:
            return "Error: HF_TOKEN not set in environment."

        image_model = os.environ.get("IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")

        prompt = self._build_prompt(outfit_description, body_type, height)

        try:
            client = InferenceClient(token=api_key)
            image = client.text_to_image(prompt, model=image_model)

            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            filename = f"outfit_visualization_{uuid.uuid4().hex[:8]}.png"
            output_file = OUTPUT_DIR / filename
            image.save(output_file)

            return (
                f"Outfit visualization saved to: {output_file}\n"
                f"Embed with: ![Outfit Visualization]({output_file})"
            )

        except Exception as exc:
            return f"Error generating outfit visualization: {exc}"
