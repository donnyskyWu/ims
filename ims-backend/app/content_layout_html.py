"""#114 内容查看入口。消毒与 #112 `layout_html` 共用，避免两套规则分叉。"""

from app.layout_html import sanitize_layout_html

__all__ = ["sanitize_layout_html"]
