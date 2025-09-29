from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import yaml

router = APIRouter()


class ValidateYamlPayload(BaseModel):
    content: str
    repo_type: str = "model"


@router.post("/validate-yaml")
def validate_yaml(body: ValidateYamlPayload):
    try:
        yaml.safe_load(body.content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")
    return {"valid": True}


@router.get("/whoami-v2")
def whoami_v2():
    return {
        "name": "me",
        "type": "user",
        "displayName": "me",
        "email": None,
        "orgs": [],
    }
