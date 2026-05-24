"""Bad smell: Duplicated Code - esperado: Template Method."""


class CustomerCSVImporter:
    def import_rows(self, raw_rows: list[str]) -> list[dict]:
        if not raw_rows:
            raise ValueError("empty import")
        imported = []
        for raw_row in raw_rows:
            columns = raw_row.split(",")
            if len(columns) != 3:
                raise ValueError("invalid customer row")
            imported.append({"name": columns[0].strip(), "email": columns[1].strip(), "city": columns[2].strip()})
        return imported


class CustomerJSONImporter:
    def import_rows(self, raw_rows: list[dict]) -> list[dict]:
        if not raw_rows:
            raise ValueError("empty import")
        imported = []
        for raw_row in raw_rows:
            if "name" not in raw_row or "email" not in raw_row or "city" not in raw_row:
                raise ValueError("invalid customer row")
            imported.append(
                {
                    "name": raw_row["name"].strip(),
                    "email": raw_row["email"].strip(),
                    "city": raw_row["city"].strip(),
                }
            )
        return imported


class CustomerFixedWidthImporter:
    def import_rows(self, raw_rows: list[str]) -> list[dict]:
        if not raw_rows:
            raise ValueError("empty import")
        imported = []
        for raw_row in raw_rows:
            if len(raw_row) < 60:
                raise ValueError("invalid customer row")
            imported.append(
                {
                    "name": raw_row[0:25].strip(),
                    "email": raw_row[25:50].strip(),
                    "city": raw_row[50:60].strip(),
                }
            )
        return imported
