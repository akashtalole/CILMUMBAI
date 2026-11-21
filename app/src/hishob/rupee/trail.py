"""What happened to my complaint (SPEC-040/R7). From a complaint id to the work order, the contractor, the cost,
whether it met the SLA and whether it held, in Marathi, Hindi or English. Built from the bundle, so it is instant
and needs no model; every sentence comes from a field the page also shows."""

from __future__ import annotations

from typing import Any

from hishob.rupee.audit import inr

TEXT = {
    "en": {
        "none": "We could not find complaint {id}.",
        "fixed": "Your complaint {id} was fixed under work order {wo} by {contractor}, on {done}. It cost {cost}.",
        "sla_yes": "It was finished within the {sla}-hour target.",
        "sla_no": "It was not finished within the {sla}-hour target.",
        "held": "The repair has held: it was not reopened within 30 days.",
        "failed": "The repair did not last: the problem came back within 30 days.",
        "dup": "It was treated as a duplicate of another complaint about the same problem.",
        "flag": "The records raise a question about this bill: {reason}.",
        "open": "Your complaint {id} is still open, with no work order yet. It was filed on {filed}.",
        "overdue": "It is past the {sla}-hour target for this kind of problem. You can take it to the {office}.",
        "rejected": "Your complaint {id} was closed as: {status}.",
        "forwarded": "Your complaint {id} was sent on: {status}. BMC is not the agency doing this repair.",
    },
    "mr": {
        "none": "तक्रार {id} सापडली नाही.",
        "fixed": "तुमची तक्रार {id} काम आदेश {wo} अंतर्गत {contractor} यांनी {done} रोजी दुरुस्त केली. खर्च {cost}.",
        "sla_yes": "काम {sla} तासांच्या मुदतीत पूर्ण झाले.",
        "sla_no": "काम {sla} तासांच्या मुदतीत पूर्ण झाले नाही.",
        "held": "दुरुस्ती टिकली: ३० दिवसांत तक्रार पुन्हा उघडली नाही.",
        "failed": "दुरुस्ती टिकली नाही: ३० दिवसांत समस्या परत आली.",
        "dup": "याच समस्येच्या दुसऱ्या तक्रारीची दुहेरी तक्रार म्हणून ती नोंदवली गेली.",
        "flag": "या बिलाबद्दल नोंदींमध्ये प्रश्न आहे: {reason}.",
        "open": "तुमची तक्रार {id} अजून उघडी आहे, काम आदेश निघालेला नाही. ती {filed} रोजी नोंदवली.",
        "overdue": "या प्रकारच्या समस्येची {sla} तासांची मुदत उलटली आहे. तुम्ही {office} येथे पाठपुरावा करू शकता.",
        "rejected": "तुमची तक्रार {id} बंद केली: {status}.",
        "forwarded": "तुमची तक्रार {id} पुढे पाठवली: {status}. ही दुरुस्ती BMC करत नाही.",
    },
    "hi": {
        "none": "शिकायत {id} नहीं मिली.",
        "fixed": "आपकी शिकायत {id} कार्य आदेश {wo} के तहत {contractor} ने {done} को ठीक की. खर्च {cost}.",
        "sla_yes": "काम {sla} घंटे की समय-सीमा में पूरा हुआ.",
        "sla_no": "काम {sla} घंटे की समय-सीमा में पूरा नहीं हुआ.",
        "held": "मरम्मत टिकी: 30 दिनों में शिकायत दोबारा नहीं खुली.",
        "failed": "मरम्मत नहीं टिकी: 30 दिनों में समस्या लौट आई.",
        "dup": "इसे इसी समस्या की दूसरी शिकायत का दोहराव माना गया.",
        "flag": "इस बिल पर रिकॉर्ड में सवाल है: {reason}.",
        "open": "आपकी शिकायत {id} अभी खुली है, कोई कार्य आदेश नहीं निकला. यह {filed} को दर्ज हुई.",
        "overdue": "इस तरह की समस्या की {sla} घंटे की समय-सीमा निकल चुकी है. आप {office} में पूछ सकते हैं.",
        "rejected": "आपकी शिकायत {id} बंद की गई: {status}.",
        "forwarded": "आपकी शिकायत {id} आगे भेजी गई: {status}. यह मरम्मत BMC नहीं करती.",
    },
}
SLA_BY_SEVERITY = {5: 24, 4: 48, 3: 72, 2: 120, 1: 168}


class Trail:
    def __init__(self, bundle: dict[str, Any], work_orders: dict[str, dict[str, Any]]) -> None:
        self.complaints = {c["complaint_id"]: c for c in bundle["complaints"]}
        self.flags: dict[str, list[dict[str, Any]]] = {}
        for f in bundle["flags"]:
            self.flags.setdefault(f["work_order_id"], []).append(f)
        self.work_orders = work_orders
        self.offices = {w["ward_code"]: w["office"] for w in bundle["wards"]}
        self.severity: dict[str, int] = bundle["summary"].get("severity", {})

    def __call__(self, complaint_id: str, lang: str = "en") -> dict[str, Any] | None:
        t = TEXT.get(lang, TEXT["en"])
        c = self.complaints.get(complaint_id.strip().upper())
        if c is None:
            return None
        wo = self.work_orders.get(c["work_order_id"]) if c["work_order_id"] else None
        lines: list[str] = []
        flags = self.flags.get(c["work_order_id"], []) if wo else []
        if wo:
            lines.append(
                t["fixed"].format(
                    id=c["complaint_id"],
                    wo=wo["work_order_id"],
                    contractor=wo["contractor_name"],
                    done=wo["completed_at"][:10],
                    cost=inr(float(wo["cost_inr"])),
                )
            )
            lines.append(t["sla_yes" if wo["sla_met"] == "Y" else "sla_no"].format(sla=wo["sla_hours"]))
            lines.append(t["failed" if wo["reopened_within_30d"] == "Y" else "held"])
            if c["state"] == "duplicate of a fixed one":
                lines.append(t["dup"])
            for f in flags:
                if f["rule"] in {"overbilled", "duplicate", "dlp_paid"}:
                    lines.append(t["flag"].format(reason=f["reason"]))
        elif c["state"].startswith("open"):
            lines.append(t["open"].format(id=c["complaint_id"], filed=c["received_at"][:10]))
            if c["state"] == "open, overdue":
                sla = SLA_BY_SEVERITY.get(self.severity.get(c["category"], 3), 72)
                lines.append(t["overdue"].format(sla=sla, office=self.offices.get(c["ward_code"], "ward office")))
        elif c["state"] == "forwarded":
            lines.append(t["forwarded"].format(id=c["complaint_id"], status=c["status"]))
        else:
            lines.append(t["rejected"].format(id=c["complaint_id"], status=c["status"]))
        return {"complaint": c, "work_order": wo, "flags": flags, "answer": " ".join(lines), "lang": lang}
