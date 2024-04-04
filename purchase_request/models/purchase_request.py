from odoo import models, fields, api, _
import xlwt
import os
from io import BytesIO

from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _description = 'Yêu cầu mua hàng'

    name = fields.Char(string='STT',Tracking=True , required=True, copy=False, readonly=True,index=True, default=lambda self: _('PR'))
    department_id = fields.Many2one('hr.department',required=True, string='Bộ phận', compute='_compute_creator_department', store=True)
    request_id = fields.Many2one('res.users',required=True, string='Người tạo yêu cầu')
    approver_id = fields.Many2one('res.users', string='Người phê duyệt')
    date = fields.Date(string='Ngày tạo', default=fields.Date.today )
    date_approve = fields.Date(string='Ngày phê duyệt' )
    request_line_ids = fields.One2many('purchase.request.line', 'request_id')
    description = fields.Text(string='Mô tả')
    state = fields.Selection([('draft', 'Dự Thảo'), ('wait', 'Chờ duyệt'), ('approved', 'Đã phê duyệt'),('refused', 'Đã từ chối'), ('cancel', 'Hoàn thành')],
                             string='Trạng thái', default='draft',readonly=True)
    total_qty = fields.Float(string='Tổng số lượng', compute='_compute_total_qty', store=True)
    total_amount = fields.Float(string='Tổng giá trị', compute='_compute_total_amount', store=True)
    have_write_right = fields.Boolean(string='Have write right', compute="_compute_have_write_right")
    go = fields.Boolean(string="create", default=False)
    def returns(self):
        # button
        self.write({'state': "wait"})
        return self.env.ref('purchase.report_purchase_quotation')
    def QL(self):
        # button
        self.write({'state': "draft"})
        return self.env.ref('purchase.report_purchase_quotation')
    def BTW(self):
        # button
        self.write({'state': "approved"})
        return self.env.ref('purchase.report_purchase_quotation')
    def TC(self):
        # button
        self.write({'state': "refused"})
        return self.env.ref('purchase.report_purchase_quotation')

    @api.model
    #tự dộng điền người tạo yêu cầu
    def default_get(self, fields):
        defaults = super(PurchaseRequest, self).default_get(fields)
        defaults['request_id'] = self.env.user.id
        return defaults
    @api.depends('request_id')
    # chọn người phê duyệt tự động chọn phòng ban
    def _compute_creator_department(self):
        for record in self:
            creator = record.request_id
            if creator:
                record.department_id = creator.department_id
    @api.onchange('department_id')
    #chọn phòng ban tự động chọn quản lý phòng ban đó
    def _onchange_department_id(self):
        if self.department_id:
            approver = self.env['res.users'].search([('department_id', '=', self.department_id.id)], limit=1)
            if approver:
                self.approver_id = approver.id
            else:
                self.approver_id = False
    @api.onchange('name')
    #phân quyền
    def _compute_have_write_right(self):
        if self.env.user.has_group('purchase_request.group_user'):
            self.have_write_right = False #nếu False thì goup_user có quyền
        if self.env.user.has_group('purchase_request.group_admin'):
            self.have_write_right = True #nếu True thì goup_admin có quyền
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('purchase.request')
        if self.go == False:
            vals['go'] = True
        return super(PurchaseRequest, self).create(vals)

    @api.depends('request_line_ids.qty')
    #tính toán
    def _compute_total_qty(self):
        for request in self:
            request.total_qty = sum(request.request_line_ids.mapped('qty'))
    @api.depends('request_line_ids.total')
    # tính toán
    def _compute_total_amount(self):
        for request in self:
            request.total_amount = sum(request.request_line_ids.mapped('total'))
    @api.depends()
    def action_delete_purchase_request(self):
        for record in self:
            record.unlink()
    @api.depends()
    def unlink(self):
        for record in self:
            if record.state == 'draft':
                super(PurchaseRequest, record).unlink()
            else:
                 raise ValueError('Bạn không thể xóa bản ghi không ở trạng thái "draft".')
    @api.model
    def create(self, vals):
        vals['request_id'] = self.env.user.id  # Gán người tạo là người đang thao tác
        vals['name'] = self.env['ir.sequence'].next_by_code('purchase.request')
        if 'state' in vals and vals['state'] != 'draft':
            raise UserError('Bạn không thể tạo chi tiết yêu cầu ở trạng thái không phải "draft".')
        return super(PurchaseRequest, self).create(vals)

    def creates(self, values):
        if 'state' in values and values['state'] != 'draft':
            raise UserError('Bạn không thể tạo chi tiết yêu cầu ở trạng thái không phải "draft".')
        return super(PurchaseRequest, self).create(values)

    # @api.depends()
    # def write(self, values):
    #     for record in self:
    #         if record.state != 'draft':
    #             raise ValueError('Bạn không thể sửa chi tiết yêu cầu ở trạng thái không phải "draft".')
    #         return super(PurchaseRequest, self).write(values)

    def export_to_excel(self):
        # Kiểm tra xem yêu cầu mua hàng ở trạng thái phê duyệt hay không
        approved_records = self.search([('state', '=', 'approved')])
        if not approved_records:
            # Nếu không có yêu cầu nào ở trạng thái phê duyệt, không thực hiện xuất Excel
            return

        # Tạo một workbook mới
        wb = xlwt.Workbook()
        ws = wb.add_sheet('Purchase Request')

        # Đặt tiêu đề cho các cột
        columns = ['STT', 'Sản Phẩm', 'Số Lượng', 'Đơn vị tính']
        for col, column_name in enumerate(columns):
            ws.write(0, col, column_name)

        # Lặp qua các yêu cầu mua hàng và điền dữ liệu vào worksheet
        row = 0
        for request in approved_records:
            for line in request.request_line_ids:
                ws.write(row + 1, 0, line.request_id.name)
                ws.write(row + 1, 1, line.product_id.name)
                ws.write(row + 1, 2, line.qty)
                ws.write(row + 1, 3, line.uom_id.name)
                row +=1

        # Lưu workbook vào một tệp Excel
        wb.save('purchase_request.xls')
        return True

