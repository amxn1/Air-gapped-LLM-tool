"""
Unit tests for ModelManager and lifecycle operations.
"""
from apps.api.database import SessionLocal
from services.inference.model_manager import (
    stage_model_profile,
    activate_model_profile,
    get_active_model_profile,
    list_model_profiles,
    rollback_model_profile,
)


def test_model_lifecycle_staging_and_activation():
    db = SessionLocal()
    try:
        # Stage new model
        staged = stage_model_profile(
            db=db,
            model_name="mistral-7b-instruct",
            version="1.0",
            format="GGUF",
            quantization="q4_k_m",
            hardware_profile="CPU/GPU",
            checksum="abc123sha256"
        )
        assert staged.id is not None
        assert staged.status == "staged"

        # Activate model
        activated = activate_model_profile(db, staged.id)
        assert activated is not None
        assert activated.status == "active"

        # Verify active model lookup
        active = get_active_model_profile(db)
        assert active.id == staged.id
        assert active.model_name == "mistral-7b-instruct"
    finally:
        db.close()
