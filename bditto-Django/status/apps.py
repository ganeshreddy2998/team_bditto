from django.apps import AppConfig


class StatusConfig(AppConfig):
    name = 'status'
    
    def ready(self):
        import status.signals
