{
    'name': "Purchase Request",
    'summary': """ Quản lý yêu cầu mua hàng """,
    'description': """ Quản lý yêu cầu mua hàng""",
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['purchase', 'hr', 'product'],
    'data': [
        'demo/product_data.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/purchase_sequence.xml',
        'views/purchase_request_views.xml',
        'views/purchase_request_line_views.xml',
    ],
}