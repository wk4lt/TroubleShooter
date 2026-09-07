#!/usr/bin/env python3
import json

from app.config import load_settings
from app.runtime.knowledge_runtime import KnowledgeRuntime


if __name__ == "__main__":
    runtime = KnowledgeRuntime(load_settings())
    print(json.dumps(runtime.list_knowledge_bases(), indent=2))
