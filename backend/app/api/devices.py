"""Devices API: register and list devices."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.device import Device
from app.schemas.device import DeviceCreate, DeviceOut

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.post("", response_model=DeviceOut, status_code=201)
def create_device(payload: DeviceCreate, db: Session = Depends(get_db)):
    existing = db.query(Device).filter_by(name=payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Device name already exists")
    device = Device(name=payload.name, vendor=payload.vendor.lower() or "unknown")
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.get("", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db)):
    return db.query(Device).order_by(Device.id.desc()).all()


@router.get("/{device_id}", response_model=DeviceOut)
def get_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).filter_by(id=device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device
