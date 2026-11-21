"""Identidad de presentación, independiente de las categorías de análisis."""
import os
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Branding(BaseModel):
    model_config = ConfigDict(extra='forbid')
    app_name: str = Field(default='Conversación viva', min_length=1, max_length=80)
    organization: str = Field(default='MinAmbiente · Laboratorio de ideas', min_length=1, max_length=120)
    description: str = Field(default='Una conversación que construimos juntos', min_length=1, max_length=180)
    center_top: str = Field(default='DIÁLOGO', min_length=1, max_length=24)
    center_bottom: str = Field(default='AMBIENTAL', min_length=1, max_length=24)
    panel_heading: str = Field(default='Ahora conversamos sobre', min_length=1, max_length=100)
    accent_color: str = Field(default='#287a38', pattern=r'^#[0-9a-fA-F]{6}$')

    @field_validator('app_name', 'organization', 'description', 'center_top', 'center_bottom', 'panel_heading', mode='before')
    @classmethod
    def clean_text(cls, value):
        return value.strip() if isinstance(value, str) else value


def environmental_branding():
    return Branding().model_dump()


def initial_branding():
    values = {key: os.environ['APP_' + key.upper()] for key in Branding.model_fields if 'APP_' + key.upper() in os.environ}
    if 'APP_NAME' in os.environ:
        values['app_name'] = os.environ['APP_NAME']
    return Branding(**values).model_dump()
