import json
import hashlib
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

from .types.errors import AgentAuthError
from .utils.crypto import sha256_hash
from .utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RealNameCredential:
    credential_id: str
    holder_did: str
    issuer: str
    real_name: str
    id_number: str
    credential_type: str
    issued_at: str
    expires_at: Optional[str] = None
    revoked: bool = False


@dataclass
class RealNameVerificationRequest:
    request_id: str
    holder_did: str
    credential_data: Dict[str, Any]
    status: str
    created_at: str


class RealNameAuthenticator:
    def __init__(self):
        self._credentials: Dict[str, RealNameCredential] = {}
        self._verification_requests: Dict[str, RealNameVerificationRequest] = {}
        self._verified_holders: Dict[str, str] = {}

    def create_credential(
        self,
        holder_did: str,
        real_name: str,
        id_number: str,
        issuer: str = "diap-authority",
        validity_days: int = 365,
    ) -> RealNameCredential:
        credential_id = self._generate_credential_id(holder_did, id_number)

        issued_at = datetime.utcnow()
        expires_at = issued_at + timedelta(days=validity_days)

        credential = RealNameCredential(
            credential_id=credential_id,
            holder_did=holder_did,
            issuer=issuer,
            real_name=real_name,
            id_number=self._mask_id_number(id_number),
            credential_type="IDCard",
            issued_at=issued_at.isoformat() + "Z",
            expires_at=expires_at.isoformat() + "Z",
        )

        self._credentials[credential_id] = credential

        logger.info(f"Created real-name credential for: {holder_did}")
        return credential

    def verify_credential(
        self,
        credential_id: str,
        real_name: str,
        id_number: str,
    ) -> bool:
        credential = self._credentials.get(credential_id)
        if not credential:
            logger.warning(f"Credential not found: {credential_id}")
            return False

        if credential.revoked:
            logger.warning(f"Credential revoked: {credential_id}")
            return False

        if credential.expires_at:
            expires = datetime.fromisoformat(
                credential.expires_at.replace("Z", "+00:00")
            )
            if datetime.utcnow() > expires.replace(tzinfo=None):
                logger.warning(f"Credential expired: {credential_id}")
                return False

        if not self._verify_id_data(credential, real_name, id_number):
            return False

        self._verified_holders[credential.holder_did] = credential_id

        logger.info(f"Credential verified for holder: {credential.holder_did}")
        return True

    def revoke_credential(self, credential_id: str) -> bool:
        if credential_id in self._credentials:
            self._credentials[credential_id].revoked = True

            holder_did = self._credentials[credential_id].holder_did
            if holder_did in self._verified_holders:
                del self._verified_holders[holder_did]

            logger.info(f"Credential revoked: {credential_id}")
            return True

        return False

    def get_credential(self, credential_id: str) -> Optional[RealNameCredential]:
        return self._credentials.get(credential_id)

    def get_credential_by_holder(self, holder_did: str) -> Optional[RealNameCredential]:
        for cred in self._credentials.values():
            if cred.holder_did == holder_did:
                return cred
        return None

    def is_holder_verified(self, holder_did: str) -> bool:
        verified_cred_id = self._verified_holders.get(holder_did)
        if not verified_cred_id:
            return False

        credential = self._credentials.get(verified_cred_id)
        if not credential or credential.revoked:
            return False

        if credential.expires_at:
            expires = datetime.fromisoformat(
                credential.expires_at.replace("Z", "+00:00")
            )
            if datetime.utcnow() > expires.replace(tzinfo=None):
                return False

        return True

    def create_verification_request(
        self,
        holder_did: str,
        credential_data: Dict[str, Any],
    ) -> RealNameVerificationRequest:
        request = RealNameVerificationRequest(
            request_id=self._generate_request_id(holder_did),
            holder_did=holder_did,
            credential_data=credential_data,
            status="pending",
            created_at=datetime.utcnow().isoformat() + "Z",
        )

        self._verification_requests[request.request_id] = request

        return request

    def approve_verification_request(
        self,
        request_id: str,
        real_name: str,
        id_number: str,
    ) -> bool:
        if request_id not in self._verification_requests:
            return False

        request = self._verification_requests[request_id]
        request.status = "approved"

        self.create_credential(
            holder_did=request.holder_did,
            real_name=real_name,
            id_number=id_number,
        )

        logger.info(f"Verification request approved: {request_id}")
        return True

    def reject_verification_request(
        self,
        request_id: str,
        reason: Optional[str] = None,
    ) -> bool:
        if request_id not in self._verification_requests:
            return False

        request = self._verification_requests[request_id]
        request.status = "rejected"

        logger.info(f"Verification request rejected: {request_id} - {reason}")
        return True

    def get_verification_request(
        self, request_id: str
    ) -> Optional[RealNameVerificationRequest]:
        return self._verification_requests.get(request_id)

    def _generate_credential_id(self, holder_did: str, id_number: str) -> str:
        data = f"{holder_did}:{id_number}:{datetime.utcnow().isoformat()}"
        return sha256_hash(data.encode()).hex()[:16]

    def _generate_request_id(self, holder_did: str) -> str:
        data = f"{holder_did}:{datetime.utcnow().isoformat()}"
        return sha256_hash(data.encode()).hex()[:16]

    def _mask_id_number(self, id_number: str) -> str:
        if len(id_number) <= 4:
            return "*" * len(id_number)
        return id_number[:2] + "*" * (len(id_number) - 4) + id_number[-2:]

    def _verify_id_data(
        self,
        credential: RealNameCredential,
        real_name: str,
        id_number: str,
    ) -> bool:
        return (
            credential.real_name == real_name
            and credential.id_number == self._mask_id_number(id_number)
        )


from datetime import timedelta
