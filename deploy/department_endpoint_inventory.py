"""Inventory department-scope exposure. This is NOT an authorization test."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent / 'backend/ruoyi-admin/src/main/java/com/ruoyi/web/controller/equipment'
EXPECTED = {'EquipmentController.java': 7, 'EquipmentDepartmentController.java': 4,
 'EquipmentOverviewController.java': 7, 'FaultCodeController.java': 4,
 'InspectionController.java': 6, 'InspectionPhotoController.java': 5,
 'InspectionTemplateController.java': 2, 'MaintenanceController.java': 7,
 'WorkOrderController.java': 13, 'WorkOrderPhotoController.java': 3}
PATTERN = re.compile(r'@(Get|Post|Put|Delete|Patch)Mapping(?:\(([^\n]*)\))?')
failed = False
for file in sorted(ROOT.glob('*Controller.java')):
    text = file.read_text(encoding='utf-8')
    base = re.search(r'@RequestMapping\("([^\"]+)"\)', text)
    matches = list(PATTERN.finditer(text))
    if file.name not in EXPECTED or len(matches) != EXPECTED[file.name] or base is None:
        print('REVIEW REQUIRED:', file.name, 'endpoint count', len(matches))
        failed = True
    for match in matches:
        line = text.count('\n', 0, match.start()) + 1
        path = re.search(r'"([^\"]+)"', match.group(2) or '')
        print(f'{file.name}:{line} {match.group(1).upper()} {base.group(1) if base else "?"}{path.group(1) if path else ""}')
missing = set(EXPECTED) - {p.name for p in ROOT.glob('*Controller.java')}
if missing:
    print('REVIEW REQUIRED: missing controllers', ', '.join(sorted(missing)))
    failed = True
print('Inventory only; endpoint authorization is not verified.')
sys.exit(1 if failed else 0)
