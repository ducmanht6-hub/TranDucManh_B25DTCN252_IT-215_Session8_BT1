from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import date
app = FastAPI()

carriers = [
    {"id": 1, "code": "GHN", "name": "Giao Hang Nhanh",
        "max_weight_capacity": 5000, "status": "ACTIVE"},
    {"id": 2, "code": "GHTK", "name": "Giao Hang Tiet Kiem",
        "max_weight_capacity": 3000, "status": "ACTIVE"},
    {"id": 3, "code": "VTP", "name": "Viettel Post",
        "max_weight_capacity": 10000, "status": "SUSPENDED"}
]

shipments = [
    {
        "id": 1,
        "carrier_id": 1,
        "order_reference": "ORD-2026-001",
        "total_weight": 4200,
        "dispatch_date": "2026-07-01",
        "shift": "MORNING"
    }
]


class CarrierCreate(BaseModel):
    code: str = Field(..., min_length=1, description="Mã đối tác duy nhất")
    name: str = Field(..., min_length=3,
                      description="Tên đối tác tối thiểu 3 ký tự")
    max_weight_capacity: int = Field(..., gt=0,
                                     description="Tải trọng tối đa lớn hơn 0")
    status: Literal["ACTIVE", "INACTIVE", "SUSPENDED"]


class ShipmentCreate(BaseModel):
    carrier_id: int
    order_reference: str
    total_weight: int = Field(..., gt=0,
                              description="Khối lượng phải lớn hơn 0")
    dispatch_date: date
    shift: Literal["MORNING", "AFTERNOON", "NIGHT"]


@app.get("/carriers")
def get_carriers(
    keyword: Optional[str] = Query(
        None, description="Tìm theo code hoặc name"),
    status: Optional[str] = Query(
        None, description="Lọc theo trạng thái"),
    min_weight: Optional[int] = Query(
        None, description="Lọc tải trọng tối đa từ mức này trở lên")
):
    result = carriers

    if keyword:
        k = keyword.lower()
        result = [c for c in result if k in c["code"].lower()
                  or k in c["name"].lower()]

    if status:
        result = [c for c in result if c["status"] == status]

    if min_weight is not None:
        result = [c for c in result if c["max_weight_capacity"] >= min_weight]

    return result


@app.get("/carriers/{carrier_id}")
def get_carrier_by_id(carrier_id: int):
    for carrier in carriers:
        if carrier["id"] == carrier_id:
            return carrier
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail="Không tìm thấy đơn vị vận chuyển")


@app.post("/carriers", status_code=status.HTTP_201_CREATED)
def create_carrier(carrier_data: CarrierCreate):
    if any(c["code"].upper() == carrier_data.code.upper() for c in carriers):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Mã đơn vị vận chuyển đã tồn tại trên hệ thống")

    new_id = max([c["id"] for c in carriers]) + 1 if carriers else 1
    new_carrier = {
        "id": new_id,
        "code": carrier_data.code,
        "name": carrier_data.name,
        "max_weight_capacity": carrier_data.max_weight_capacity,
        "status": carrier_data.status
    }

    carriers.append(new_carrier)
    return new_carrier


@app.put("/carriers/{carrier_id}")
def update_carrier(carrier_id: int, carrier_data: CarrierCreate):
    target_carrier = None
    for c in carriers:
        if c["id"] == carrier_id:
            target_carrier = c
            break

    if not target_carrier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Không tìm thấy đơn vị vận chuyển")

    if any(c["code"].upper() == carrier_data.code.upper() and c["id"] != carrier_id for c in carriers):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Mã đơn vị vận chuyển đã tồn tại trên hệ thống")

    update_dict = dict(carrier_data)
    target_carrier.update(update_dict)
    return target_carrier


@app.delete("/carriers/{carrier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_carrier(carrier_id: int):
    global carriers
    carrier_exists = any(c["id"] == carrier_id for c in carriers)
    if not carrier_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Không tìm thấy đơn vị vận chuyển")

    carriers = [c for c in carriers if c["id"] != carrier_id]
    return {"message": "Xóa đơn vị vận chuyển thành công"}


@app.get("/shipments")
def get_shipments():
    return shipments


@app.post("/shipments", status_code=status.HTTP_201_CREATED)
def create_shipment(shipment_data: ShipmentCreate):
    carrier = None
    for c in carriers:
        if c["id"] == shipment_data.carrier_id:
            carrier = c
            break

    if not carrier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Carrier ID không tồn tại.")

    if carrier["status"] != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Đối tác vận chuyển đang không hoạt động.")

    if shipment_data.total_weight > carrier["max_weight_capacity"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tổng khối lượng vượt quá tải trọng tối đa của đối tác ({carrier['max_weight_capacity']})."
        )

    date_str = str(shipment_data.dispatch_date)
    is_duplicate = any(
        s["carrier_id"] == shipment_data.carrier_id and
        s["dispatch_date"] == date_str and
        s["shift"] == shipment_data.shift
        for s in shipments
    )
    if is_duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Đối tác đã được xếp lịch vào ngày và ca làm việc này.")

    new_id = max([s["id"] for s in shipments]) + 1 if shipments else 1
    new_shipment = {
        "id": new_id,
        "carrier_id": shipment_data.carrier_id,
        "order_reference": shipment_data.order_reference,
        "total_weight": shipment_data.total_weight,
        "dispatch_date": date_str,
        "shift": shipment_data.shift
    }

    shipments.append(new_shipment)
    return new_shipment
