package com.ruoyi.web.controller.equipment;

import java.util.HashMap;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import java.time.LocalDate;
import org.springframework.web.bind.annotation.RestController;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;

@RestController
@RequestMapping("/equipment/overview")
public class EquipmentOverviewController extends BaseController {
    private final JdbcTemplate jdbc;
    private final DepartmentScopeAccess access;
    public EquipmentOverviewController(JdbcTemplate jdbc,DepartmentScopeAccess access) { this.jdbc=jdbc; this.access=access; }
    private String filter(java.util.List<Object> args) {
        if (!access.enabled()) return "";
        var f=DepartmentScopeSql.equipmentPredicate(access.current("equipment:order:viewAll"),"e.id");
        args.addAll(f.args()); return " AND ("+f.sql()+")";
    }
    @PreAuthorize("@ss.hasPermi('equipment:order:viewAll')")
    @GetMapping("/costs")
    public AjaxResult costs(@RequestParam(required=false) LocalDate startDate, @RequestParam(required=false) LocalDate endDate) {
        if ((startDate==null)!=(endDate==null) || (startDate!=null && (startDate.isAfter(endDate) || java.time.temporal.ChronoUnit.DAYS.between(startDate,endDate)>366))) return error("请选择不超过一年的有效日期范围");
        String sql="SELECT COALESCE(SUM(c.amount),0) AS total,COALESCE(SUM(CASE WHEN c.category='LABOR' THEN c.amount ELSE 0 END),0) AS labor,COALESCE(SUM(CASE WHEN c.category='PARTS' THEN c.amount ELSE 0 END),0) AS parts,COALESCE(SUM(CASE WHEN c.category='OTHER' THEN c.amount ELSE 0 END),0) AS other,COUNT(DISTINCT r.work_order_id) AS order_count,COUNT(DISTINCT r.id) AS repair_count FROM ems_repair_cost c JOIN ems_repair_cost_link l ON l.cost_id=c.id JOIN ems_work_order_repair r ON r.id=l.repair_id JOIN ems_work_order w ON w.id=r.work_order_id JOIN ems_equipment e ON e.id=w.equipment_id WHERE 1=1";
        var args=new java.util.ArrayList<Object>();
        if(startDate!=null){ sql+=" AND r.repair_date>=? AND r.repair_date<=?"; args.add(startDate); args.add(endDate); }
        sql+=filter(args); return success(jdbc.queryForMap(sql,args.toArray()));
    }
    @PreAuthorize("@ss.hasPermi('equipment:order:viewAll')")
    @GetMapping("/costs/orders")
    public AjaxResult costOrders(@RequestParam(required=false) LocalDate startDate, @RequestParam(required=false) LocalDate endDate, @RequestParam(required=false) Long beforeId) {
        if ((startDate==null)!=(endDate==null) || (startDate!=null && (startDate.isAfter(endDate) || java.time.temporal.ChronoUnit.DAYS.between(startDate,endDate)>366)) || (beforeId!=null && beforeId<=0)) return error("日期范围或分页参数无效");
        String sql="SELECT w.id,w.status,w.description,e.code AS equipment_code,e.name AS equipment_name,SUM(c.amount) AS total,SUM(CASE WHEN c.category='LABOR' THEN c.amount ELSE 0 END) AS labor,SUM(CASE WHEN c.category='PARTS' THEN c.amount ELSE 0 END) AS parts,SUM(CASE WHEN c.category='OTHER' THEN c.amount ELSE 0 END) AS other FROM ems_work_order w JOIN ems_equipment e ON e.id=w.equipment_id JOIN ems_work_order_repair r ON r.work_order_id=w.id JOIN ems_repair_cost_link l ON l.repair_id=r.id JOIN ems_repair_cost c ON c.id=l.cost_id WHERE w.id<?";
        String tail=" GROUP BY w.id,w.status,w.description,e.code,e.name ORDER BY w.id DESC LIMIT 50";
        long cursor=beforeId==null?Long.MAX_VALUE:beforeId;
        var args=new java.util.ArrayList<Object>(); args.add(cursor);
        if(startDate!=null){sql+=" AND r.repair_date>=? AND r.repair_date<=?"; args.add(startDate); args.add(endDate);}
        sql+=filter(args); return success(jdbc.queryForList(sql+tail,args.toArray()));
    }
    @PreAuthorize("@ss.hasPermi('equipment:order:viewAll')")
    @org.springframework.transaction.annotation.Transactional(readOnly=true, timeout=60)
    @GetMapping("/costs/export")
    public void exportCosts(@RequestParam(required=false) LocalDate startDate, @RequestParam(required=false) LocalDate endDate, jakarta.servlet.http.HttpServletResponse response) throws java.io.IOException {
        AjaxResult summary=costs(startDate,endDate);
        if (!Integer.valueOf(200).equals(summary.get("code"))) { response.sendError(400,"Invalid date range"); return; }
        @SuppressWarnings("unchecked") var totals=(java.util.Map<String,Object>)summary.get("data");
        if (((Number)totals.get("order_count")).longValue()>5000) { response.sendError(413,"Too many orders; select a shorter date range"); return; }
        try (var workbook=new org.apache.poi.xssf.usermodel.XSSFWorkbook()) {
            var sheet=workbook.createSheet("维修费用工单");
            var title=sheet.createRow(0);
            title.createCell(0).setCellValue((startDate==null?"全部日期":startDate+" 至 "+endDate)+" · 含已取消工单，不含未关联维修记录的历史费用");
            var header=sheet.createRow(1);
            String[] columns={"工单号","设备编号","设备名称","工单状态","故障描述","人工费","配件费","其他费用","合计"};
            for (int i=0;i<columns.length;i++){header.createCell(i).setCellValue(columns[i]);sheet.setColumnWidth(i,i==4?40*256:18*256);}
            Long cursor=null; int index=2;
            var statuses=java.util.Map.of("REPORTED","待接单","ACCEPTED","待到场","ARRIVED","维修中","TESTING","待试运行","COMPLETED","待确认","CLOSED","已关闭","CANCELLED","已取消");
            while (true) {
                AjaxResult page=costOrders(startDate,endDate,cursor);
                @SuppressWarnings("unchecked") var rows=(java.util.List<java.util.Map<String,Object>>)page.get("data");
                for (var item:rows) {
                    var row=sheet.createRow(index++);
                    row.createCell(0).setCellValue(String.valueOf(item.get("id")));
                    row.createCell(1).setCellValue(String.valueOf(item.get("equipment_code")));
                    row.createCell(2).setCellValue(String.valueOf(item.get("equipment_name")));
                    String status=String.valueOf(item.get("status"));row.createCell(3).setCellValue(statuses.getOrDefault(status,status));
                    row.createCell(4).setCellValue(String.valueOf(item.get("description")));
                    row.createCell(5).setCellValue(((Number)item.get("labor")).doubleValue());
                    row.createCell(6).setCellValue(((Number)item.get("parts")).doubleValue());
                    row.createCell(7).setCellValue(((Number)item.get("other")).doubleValue());
                    row.createCell(8).setCellValue(((Number)item.get("total")).doubleValue());
                }
                if (rows.size()<50) break;
                cursor=((Number)rows.get(rows.size()-1).get("id")).longValue();
            }
            response.setContentType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
            response.setHeader("Content-Disposition","attachment; filename=repair-costs.xlsx");
            response.setHeader("Cache-Control","no-store");
            workbook.write(response.getOutputStream());
        }
    }
    @PreAuthorize("@ss.hasPermi('equipment:order:viewAll')")
    @GetMapping("/faults")
    public AjaxResult faults(@RequestParam(required=false) LocalDate startDate, @RequestParam(required=false) LocalDate endDate) {
        if ((startDate==null)!=(endDate==null) || (startDate!=null && (startDate.isAfter(endDate) || java.time.temporal.ChronoUnit.DAYS.between(startDate,endDate)>366))) return error("请选择不超过一年的有效日期范围");
        String sql="SELECT f.code,f.category,f.part,f.symptom,COUNT(*) AS repair_count,COUNT(DISTINCT r.work_order_id) AS order_count FROM ems_repair_fault_code f JOIN ems_work_order_repair r ON r.id=f.repair_id JOIN ems_work_order w ON w.id=r.work_order_id JOIN ems_equipment e ON e.id=w.equipment_id WHERE w.status <> 'CANCELLED'";
        String tail=" GROUP BY f.code,f.category,f.part,f.symptom ORDER BY repair_count DESC,f.code,f.category,f.part,f.symptom LIMIT 50";
        var args=new java.util.ArrayList<Object>();
        if(startDate!=null){sql+=" AND r.repair_date>=? AND r.repair_date<=?"; args.add(startDate); args.add(endDate);}
        sql+=filter(args); return success(jdbc.queryForList(sql+tail,args.toArray()));
    }
    @PreAuthorize("@ss.hasPermi('equipment:order:viewAll')")
    @GetMapping("/faults/export")
    public void exportFaults(@RequestParam(required=false) LocalDate startDate,@RequestParam(required=false) LocalDate endDate,jakarta.servlet.http.HttpServletResponse response) throws java.io.IOException {
        AjaxResult result=faults(startDate,endDate);
        if (!Integer.valueOf(200).equals(result.get("code"))) { response.sendError(400,"Invalid date range"); return; }
        @SuppressWarnings("unchecked") var rows=(java.util.List<java.util.Map<String,Object>>) result.get("data");
        response.setContentType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
        response.setHeader("Content-Disposition","attachment; filename=equipment-faults.xlsx");
        response.setHeader("Cache-Control","no-store");
        try (var workbook=new org.apache.poi.xssf.usermodel.XSSFWorkbook()) {
            var sheet=workbook.createSheet("故障代码排行");
            var title=sheet.createRow(0);
            title.createCell(0).setCellValue(startDate==null ? "累计范围 · 不含已取消工单" : startDate+" 至 "+endDate+" · 不含已取消工单");
            var header=sheet.createRow(1);
            String[] columns={"代码","类别","部位","现象","维修次数","工单数"};
            for (int i=0;i<columns.length;i++) { header.createCell(i).setCellValue(columns[i]);sheet.setColumnWidth(i,20*256); }
            int index=2;
            for (var item:rows) {
                var row=sheet.createRow(index++);
                row.createCell(0).setCellValue(String.valueOf(item.get("code")));
                row.createCell(1).setCellValue(String.valueOf(item.get("category")));
                row.createCell(2).setCellValue(String.valueOf(item.get("part")));
                row.createCell(3).setCellValue(String.valueOf(item.get("symptom")));
                row.createCell(4).setCellValue(((Number)item.get("repair_count")).doubleValue());
                row.createCell(5).setCellValue(((Number)item.get("order_count")).doubleValue());
            }
            workbook.write(response.getOutputStream());
        }
    }
    @PreAuthorize("@ss.hasPermi('equipment:order:viewAll')")
    @GetMapping("/faults/orders")
    public AjaxResult faultOrders(@RequestParam String code,@RequestParam String category,@RequestParam String part,@RequestParam String symptom,@RequestParam(required=false) LocalDate startDate,@RequestParam(required=false) LocalDate endDate,@RequestParam(required=false) Long beforeId) {
        if (code.isBlank() || code.length()>64 || category.isBlank() || category.length()>80 || part.isBlank() || part.length()>80 || symptom.isBlank() || symptom.length()>80 || (beforeId!=null && beforeId<=0)) return error("筛选参数无效");
        if ((startDate==null)!=(endDate==null) || (startDate!=null && (startDate.isAfter(endDate) || java.time.temporal.ChronoUnit.DAYS.between(startDate,endDate)>366))) return error("请选择不超过一年的有效日期范围");
        String sql="SELECT w.id,w.description,w.status,w.created_at,e.code AS equipment_code,e.name AS equipment_name FROM ems_work_order w JOIN ems_equipment e ON e.id=w.equipment_id WHERE w.id<? AND w.status<>'CANCELLED' AND EXISTS (SELECT 1 FROM ems_work_order_repair r JOIN ems_repair_fault_code f ON f.repair_id=r.id WHERE r.work_order_id=w.id AND f.code=? AND f.category=? AND f.part=? AND f.symptom=?";
        long cursor=beforeId==null?Long.MAX_VALUE:beforeId;
        var args=new java.util.ArrayList<Object>(); java.util.Collections.addAll(args,cursor,code,category,part,symptom);
        if(startDate!=null){sql+=" AND r.repair_date>=? AND r.repair_date<=?"; args.add(startDate); args.add(endDate);}
        sql+=")"; sql+=filter(args); return success(jdbc.queryForList(sql+" ORDER BY w.id DESC LIMIT 50",args.toArray()));
    }
    @PreAuthorize("@ss.hasPermi('equipment:order:viewAll')")
    @GetMapping
    public AjaxResult summary() {
        var result=new HashMap<String,Object>();
        var args=new java.util.ArrayList<Object>();
        String where=filter(args);
        result.put("equipment",jdbc.queryForMap("SELECT COUNT(*) AS total,COALESCE(SUM(e.status='ACTIVE'),0) AS active,COALESCE(SUM(e.status='RETIRED'),0) AS retired FROM ems_equipment e WHERE 1=1"+where,args.toArray()));
        result.put("orders",jdbc.queryForMap("SELECT COALESCE(SUM(w.status='REPORTED'),0) AS reported,COALESCE(SUM(w.status IN ('ACCEPTED','ARRIVED','TESTING')),0) AS accepted,COALESCE(SUM(w.status='COMPLETED'),0) AS completed,COALESCE(SUM(w.status='CLOSED'),0) AS closed FROM ems_work_order w JOIN ems_equipment e ON e.id=w.equipment_id WHERE 1=1"+where,args.toArray()));
        result.put("costs",jdbc.queryForMap("SELECT COALESCE(SUM(c.amount),0) AS total,COALESCE(SUM(CASE WHEN c.category='LABOR' THEN c.amount ELSE 0 END),0) AS labor,COALESCE(SUM(CASE WHEN c.category='PARTS' THEN c.amount ELSE 0 END),0) AS parts,COALESCE(SUM(CASE WHEN c.category='OTHER' THEN c.amount ELSE 0 END),0) AS other FROM ems_repair_cost c JOIN ems_work_order w ON w.id=c.work_order_id JOIN ems_equipment e ON e.id=w.equipment_id WHERE 1=1"+where,args.toArray()));
        return success(result);
    }
}


