from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import hashlib
import json

@dataclass
class AgentManifest:
    name: str
    version: str
    description: str
    owner_organization: str
    capabilities: List[str]
    endpoints: List[str]
    operational_bounds: Dict[str, Any]

    def compute_hash(self) -> str:
        manifest_dict = asdict(self)
        canonical_json = json.dumps(manifest_dict, sort_keys=True)
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
