"""evaluation 包测试配置。"""

from __future__ import annotations

import os
import sys

import pytest

# 将 src/ 加入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
