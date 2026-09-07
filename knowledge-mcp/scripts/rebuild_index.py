#!/usr/bin/env python3
from app.config import load_settings
from app.runtime.knowledge_runtime import KnowledgeRuntime


if __name__ == "__main__":
    print(KnowledgeRuntime(load_settings()).rebuild())
