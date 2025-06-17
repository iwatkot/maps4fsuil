from typing import Type

from tools.textures import TextureSchemaEditorTool
from tools.tool import Tool
from tools.trees import TreeSchemaEditorTool


class Section:
    title: str
    description: str
    tools: list[Type[Tool]]

    @classmethod
    def all(cls):
        return cls.__subclasses__()

    @classmethod
    def add(cls):
        for tool in cls.tools:
            tool()


class Schemas(Section):
    title = "📄 Schemas"
    description = "Tools to work with different schemas."
    tools = [TreeSchemaEditorTool, TextureSchemaEditorTool]
