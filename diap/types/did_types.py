from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class VerificationMethod:
    id: str
    vm_type: str
    controller: str
    public_key_multibase: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.vm_type,
            "controller": self.controller,
            "publicKeyMultibase": self.public_key_multibase,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationMethod":
        return cls(
            id=data["id"],
            vm_type=data["type"],
            controller=data["controller"],
            public_key_multibase=data["publicKeyMultibase"],
        )


@dataclass
class Service:
    id: str
    service_type: str
    service_endpoint: Any
    pubsub_topics: Optional[List[str]] = None
    network_addresses: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "type": self.service_type,
            "serviceEndpoint": self.service_endpoint,
        }
        if self.pubsub_topics:
            result["pubsubTopics"] = self.pubsub_topics
        if self.network_addresses:
            result["networkAddresses"] = self.network_addresses
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Service":
        return cls(
            id=data["id"],
            service_type=data["type"],
            service_endpoint=data["serviceEndpoint"],
            pubsub_topics=data.get("pubsubTopics"),
            network_addresses=data.get("networkAddresses"),
        )


@dataclass
class DIDDocument:
    context: List[str]
    id: str
    verification_method: List[VerificationMethod]
    authentication: List[str]
    service: Optional[List[Service]] = None
    created: Optional[str] = None
    updated: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "@context": self.context,
            "id": self.id,
            "verificationMethod": [vm.to_dict() for vm in self.verification_method],
            "authentication": self.authentication,
        }
        if self.service:
            result["service"] = [s.to_dict() for s in self.service]
        if self.created:
            result["created"] = self.created
        if self.updated:
            result["updated"] = self.updated
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DIDDocument":
        verification_methods = [
            VerificationMethod.from_dict(vm)
            for vm in data.get("verificationMethod", [])
        ]
        services = (
            [Service.from_dict(s) for s in data.get("service", [])]
            if data.get("service")
            else None
        )

        return cls(
            context=data.get("@context", []),
            id=data["id"],
            verification_method=verification_methods,
            authentication=data.get("authentication", []),
            service=services,
            created=data.get("created"),
            updated=data.get("updated"),
        )


@dataclass
class AgentProfile:
    avatar: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    homepage: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avatar": self.avatar,
            "name": self.name,
            "description": self.description,
            "homepage": self.homepage,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentProfile":
        return cls(
            avatar=data.get("avatar"),
            name=data.get("name"),
            description=data.get("description"),
            homepage=data.get("homepage"),
        )


@dataclass
class AgentWallet:
    address: str
    blockchain: str
    capabilities: List[str]
    spending_limit: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": self.address,
            "blockchain": self.blockchain,
            "capabilities": self.capabilities,
            "spendingLimit": self.spending_limit,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentWallet":
        return cls(
            address=data["address"],
            blockchain=data["blockchain"],
            capabilities=data.get("capabilities", []),
            spending_limit=data.get("spendingLimit"),
        )


@dataclass
class CryptoWallets:
    ethereum: Optional[List[AgentWallet]] = None
    bitcoin: Optional[List[AgentWallet]] = None
    solana: Optional[List[AgentWallet]] = None
    polygon: Optional[List[AgentWallet]] = None
    bsc: Optional[List[AgentWallet]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ethereum": [w.to_dict() for w in self.ethereum] if self.ethereum else None,
            "bitcoin": [w.to_dict() for w in self.bitcoin] if self.bitcoin else None,
            "solana": [w.to_dict() for w in self.solana] if self.solana else None,
            "polygon": [w.to_dict() for w in self.polygon] if self.polygon else None,
            "bsc": [w.to_dict() for w in self.bsc] if self.bsc else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CryptoWallets":
        return cls(
            ethereum=[AgentWallet.from_dict(w) for w in data["ethereum"]]
            if data.get("ethereum")
            else None,
            bitcoin=[AgentWallet.from_dict(w) for w in data["bitcoin"]]
            if data.get("bitcoin")
            else None,
            solana=[AgentWallet.from_dict(w) for w in data["solana"]]
            if data.get("solana")
            else None,
            polygon=[AgentWallet.from_dict(w) for w in data["polygon"]]
            if data.get("polygon")
            else None,
            bsc=[AgentWallet.from_dict(w) for w in data["bsc"]]
            if data.get("bsc")
            else None,
        )


@dataclass
class LinkedDomains:
    domains: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {"domains": self.domains}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LinkedDomains":
        return cls(domains=data["domains"])
