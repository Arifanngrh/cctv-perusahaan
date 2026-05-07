from ultralytics import YOLO

model = YOLO("yolo11n.pt")

model.train(
    data="dataset_helmet/data.yaml",
    epochs=80,
    imgsz=640,
    batch=8
)