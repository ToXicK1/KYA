from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from src.core.logging import logger
from src.domain.exceptions import (
    DomainException,
    PrivateKeyDetectedException,
    AgentNotFoundException,
    InvalidPublicKeyException,
)
import binascii
import traceback
import time

class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            logger.info(f"{request.method} {request.url.path} Completed {response.status_code} in {process_time:.2f}ms")
            return response
        except PrivateKeyDetectedException as exc:
            logger.warning(f"SECURITY ALERT: Private key rejection on {request.url.path}: {str(exc)}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "PRIVATE_KEY_FORBIDDEN",
                        "message": str(exc),
                        "details": "Private keys are strictly forbidden by KYA Zero-Trust policy."
                    }
                }
            )
        except InvalidPublicKeyException as exc:
            logger.warning(f"Invalid public key on {request.url.path}: {str(exc)}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "INVALID_PUBLIC_KEY",
                        "message": str(exc)
                    }
                }
            )
        except AgentNotFoundException as exc:
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "AGENT_NOT_FOUND",
                        "message": str(exc)
                    }
                }
            )
        except DomainException as exc:
            logger.warning(f"Domain rule violation on {request.url.path}: {str(exc)}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "DOMAIN_ERROR",
                        "message": str(exc)
                    }
                }
            )
        except (binascii.Error, ValueError) as exc:
            logger.warning(f"Bad payload encoding on {request.url.path}: {str(exc)}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "BAD_REQUEST_ENCODING",
                        "message": f"Invalid encoding in request payload: {str(exc)}"
                    }
                }
            )
        except Exception as exc:
            logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {str(exc)}\n{traceback.format_exc()}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected server error occurred."
                    }
                }
            )
