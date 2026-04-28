from dataclasses import dataclass, field


@dataclass
class Config:
    # to skip full routes add "/route", to skip prefixes, add "/route/*"
    ignored_routes: list[str] = field(default_factory=list)
    exclude_library_metrics: bool = True
    ui_config_route: str = "/config-b887e852-bd12-41f2-b057-1bd31eb5443e"
    enable_dashboard_ui: bool = True
    custom_path: str = "/metrics"
    include_in_openapi: bool = False
    ui_title: str = "FastAPI Metrics"
