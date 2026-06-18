from fastapi import APIRouter


router = APIRouter(tags=["health"])


#Tut ya vynes health, chtoby ne razduvat ostalnoy kod.
@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
