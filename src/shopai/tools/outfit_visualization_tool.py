"""
Outfit Visualization Tool
Generates an outfit visualization image using the configured IMAGE_MODEL via OpenRouter.
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


class OutfitVisualizationTool(BaseTool):
    name: str = "outfit_visualizer"
    description: str = (
        "Generates an outfit visualization image using the configured image model. "
        "Pass the outfit description and body type. "
        "Returns the saved file path for embedding in the shopping guide."
    )
    args_schema: Type[BaseModel] = OutfitVisualizationInput

    def _build_prompt(self, outfit_description: str, body_type: str) -> str:
        return (
            f"Full-body fashion photograph of a single model with a {body_type} body type. "
            f"The model is wearing: {outfit_description}. "
            "Standing in a well-lit, neutral studio with clean white background. "
            "Professional fashion editorial style — sharp focus, natural lighting. "
            "Show the complete outfit from head to toe. "
            "No text, watermarks, or logos. Square 1:1 aspect ratio."
        )

    def _run(self, outfit_description: str, body_type: str) -> str:
        try:
            from openai import OpenAI
        except ImportError:
            return "Error: 'openai' package is not installed. Run: uv add openai"

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            return "Error: OPENROUTER_API_KEY not set in environment."

        image_model = os.environ.get("IMAGE_MODEL", "x-ai/grok-2-image-generation")
        if image_model.startswith("openrouter/"):
            image_model = image_model[len("openrouter/"):]
        image_model = image_model.replace(":free", "")

        prompt = self._build_prompt(outfit_description, body_type)

        try:
            client = OpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
            )

            response = client.images.generate(
                model=image_model,
                prompt=prompt,
                n=1,
                size="1024x1024",
                response_format="b64_json",
            )

            b64_data = response.data[0].b64_json
            if not b64_data:
                # Some models return a URL instead
                image_url = response.data[0].url or ""
                return f"Outfit visualization URL: {image_url}"

            import base64
            image_bytes = base64.b64decode(b64_data)

            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            filename = f"outfit_visualization_{uuid.uuid4().hex[:8]}.png"
            output_file = OUTPUT_DIR / filename
            output_file.write_bytes(image_bytes)

            return (
                f"Outfit visualization saved to: {output_file}\n"
                f"Embed with: ![Outfit Visualization]({output_file})"
            )

        except Exception as exc:
            return f"Error generating outfit visualization: {exc}"
