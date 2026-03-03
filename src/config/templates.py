"""
Template + Design registry.
Maps (ratio, template, design) → module path + class name.
Each ratio has its own templates, and each template has its own designs.
"""

import importlib

# Registry: (ratio, template, design) → "module.path.ClassName"
TEMPLATE_REGISTRY = {
    ("instagram_post", "hook", "design1"): "src.templates.instagram_post.hook.design1.HookDesign1",
    ("instagram_post", "content", "design1"): "src.templates.instagram_post.content.design1.ContentDesign1",
    ("instagram_story", "hook", "design1"): "src.templates.instagram_story.hook.design1.HookDesign1",
    ("instagram_story", "content", "design1"): "src.templates.instagram_story.content.design1.ContentDesign1",
    ("instagram_feed", "hook", "design1"): "src.templates.instagram_feed.hook.design1.HookDesign1",
    ("instagram_feed", "content", "design1"): "src.templates.instagram_feed.content.design1.ContentDesign1",
}


def get_design_class(ratio: str, template: str, design: str):
    """
    Dynamically import and return the design class for a given
    ratio + template + design combination.
    """
    key = (ratio, template, design)
    if key not in TEMPLATE_REGISTRY:
        available = ", ".join(f"{r}/{t}/{d}" for r, t, d in TEMPLATE_REGISTRY.keys())
        raise KeyError(
            f"Unknown combo '{ratio}/{template}/{design}'. Available: {available}"
        )

    full_path = TEMPLATE_REGISTRY[key]
    module_path, class_name = full_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)
