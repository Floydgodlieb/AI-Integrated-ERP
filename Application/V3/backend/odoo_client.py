import json
import xmlrpc.client
import urllib.request


class OdooClient:
    def __init__(self, url: str, db: str, username: str, password: str, teams_webhook_url: str = ""):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.teams_webhook_url = teams_webhook_url
        self.uid = None
        self.models = None
        self._authenticate()

    def _authenticate(self):
        common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
        self.uid = common.authenticate(self.db, self.username, self.password, {})
        if not self.uid:
            raise ConnectionError("Odoo authentication failed")
        self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')

    def send_teams_notification(self, title: str, message: str, is_success: bool = True):
        status_color = "Good" if is_success else "Attention"
        status_label = "SUCCESS" if is_success else "ERROR"
        payload = {
            "type": "message",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "body": [{
                        "type": "Container",
                        "items": [
                            {"type": "TextBlock", "size": "Medium", "weight": "Bolder", "text": f"Odoo Agent Alert: {title}"},
                            {"type": "TextBlock", "text": f"Status: **{status_label}**", "color": status_color, "weight": "Bolder", "spacing": "Small"},
                            {"type": "TextBlock", "text": message, "wrap": True, "spacing": "Medium"}
                        ]
                    }],
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.4"
                }
            }]
        }
        try:
            req = urllib.request.Request(
                self.teams_webhook_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req) as response:
                if response.status in [200, 202]:
                    pass
        except Exception:
            pass

    def search_read(self, model: str, domain: list, fields: list) -> list:
        if not domain or domain == [[]]:
            domain = []
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, "search_read",
            [domain],
            {"fields": fields}
        )

    def create(self, model: str, values: dict) -> dict:
        corrected = self._apply_auto_corrections(model, values)
        new_id = self.models.execute_kw(
            self.db, self.uid, self.password,
            model, "create",
            [corrected]
        )
        if self.teams_webhook_url:
            self.send_teams_notification(
                title=f"ERP Record Created: {model}",
                message=f"Successfully generated a new entry under **{model}** with Database ID: `{new_id}`.",
                is_success=True
            )
        return {"status": "success", "created_id": new_id}

    def _apply_auto_corrections(self, model: str, values: dict) -> dict:
        values = dict(values)
        if model == 'sale.order' and 'order_line' in values:
            raw_lines = values['order_line']
            if raw_lines and isinstance(raw_lines, list):
                for line in raw_lines:
                    if isinstance(line, list) and len(line) == 3 and isinstance(line[2], dict):
                        line_data = line[2]
                        if 'quantity' in line_data:
                            line_data['product_uom_qty'] = line_data.pop('quantity')

        if model == 'account.move' and 'invoice_line_ids' in values:
            raw_lines = values['invoice_line_ids']
            if raw_lines and isinstance(raw_lines, list):
                if not isinstance(raw_lines[0], list):
                    values['invoice_line_ids'] = [[0, 0, line] if isinstance(line, dict) else line for line in raw_lines]
                for line in values['invoice_line_ids']:
                    if isinstance(line, list) and len(line) == 3 and isinstance(line[2], dict):
                        line_data = line[2]
                        if 'product_uom_qty' in line_data:
                            line_data['quantity'] = line_data.pop('product_uom_qty')
        return values
