from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from advance_report.models import Contract, ContractLine, Payment, Work, WorkLine
from advance_report.money import ZERO


def allocation_order(works: list[Work], as_of: date) -> list[Work]:
    """Сначала принятые (по дате приёмки), потом planned, cancelled в конце."""

    def key(w: Work) -> tuple:
        status = w.status_as_of(as_of)
        if status == "done":
            return (0, w.completed_at or date.min, w.work_id)
        if status == "planned":
            return (1, date.max, w.work_id)
        return (2, date.max, w.work_id)

    return sorted(works, key=key)


def build_report(
    contracts: dict[str, Contract],
    works: list[Work],
    payments: list[Payment],
    as_of: date,
) -> list[ContractLine]:
    works_by_contract: dict[str, list[Work]] = defaultdict(list)
    for w in works:
        works_by_contract[w.contract_id].append(w)

    paid_direct: dict[str, Decimal] = defaultdict(lambda: ZERO)
    paid_pool: dict[str, Decimal] = defaultdict(lambda: ZERO)
    paid_total_by_contract: dict[str, Decimal] = defaultdict(lambda: ZERO)

    for p in payments:
        eff = p.effective_paid(as_of)
        if eff == ZERO:
            continue
        paid_total_by_contract[p.contract_id] += eff
        if p.work_id:
            paid_direct[p.work_id] += eff
        else:
            paid_pool[p.contract_id] += eff

    result: list[ContractLine] = []
    for contract_id in sorted(contracts.keys()):
        contract = contracts[contract_id]
        c_works = works_by_contract.get(contract_id, [])
        paid_map: dict[str, Decimal] = {
            w.work_id: paid_direct.get(w.work_id, ZERO) for w in c_works
        }
        pool = paid_pool.get(contract_id, ZERO)

        for w in allocation_order(c_works, as_of):
            obl = w.obligation(as_of)
            already = paid_map[w.work_id]
            if already >= obl:
                continue
            need = obl - already
            take = need if need <= pool else pool
            paid_map[w.work_id] = already + take
            pool -= take
            if pool == ZERO:
                break

        surplus = pool
        for w in c_works:
            obl = w.obligation(as_of)
            if paid_map[w.work_id] > obl:
                surplus += paid_map[w.work_id] - obl
                paid_map[w.work_id] = obl

        work_lines = [
            WorkLine(
                work=w,
                status=w.status_as_of(as_of),
                price=w.price,
                obligation=w.obligation(as_of),
                paid=paid_map[w.work_id],
            )
            for w in sorted(c_works, key=lambda x: x.work_id)
        ]
        result.append(
            ContractLine(
                contract=contract,
                work_lines=work_lines,
                paid_total=paid_total_by_contract.get(contract_id, ZERO),
                unallocated_surplus=surplus,
            )
        )
    return result
