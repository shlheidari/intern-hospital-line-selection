from line.models import Visitor
from preventconcurrentlogins.middleware import PreventConcurrentLoginsMiddleware

class FixedPreventConcurrentLoginsMiddleware(PreventConcurrentLoginsMiddleware):
    def process_request(self, request):
        if hasattr(request.user, 'is_authenticated') and request.user.is_authenticated:
            # Enforce single visitor before proceeding
            Visitor.enforce_single_visitor(request.user)
            return super().process_request(request)
        return None