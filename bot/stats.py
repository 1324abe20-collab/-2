"""Текст блоку статистики."""

import config
import cards


def build_stats_text(stats):
    by_status = stats.get("by_status", {})
    total = stats.get("total", 0)

    lines = [
        "📊 <b>Статистика замовлень</b>",
        "━━━━━━━━━━━━━━",
        "📦 Всього: <b>{}</b>".format(total),
    ]

    for status in config.STATUS_ORDER:
        emoji, label = config.STATUSES[status]
        lines.append("{} {}: {}".format(emoji, label, by_status.get(status, 0)))

    lines.extend(
        [
            "━━━━━━━━━━━━━━",
            "📅 Сьогодні: <b>{}</b> (успішних: {})".format(
                stats.get("today", 0), stats.get("done_today", 0)
            ),
            "🗓 За 7 днів: <b>{}</b>".format(stats.get("week", 0)),
            "🗓 За 30 днів: <b>{}</b>".format(stats.get("month", 0)),
            "━━━━━━━━━━━━━━",
            "💰 Виторг (успішні): <b>{}</b>".format(cards.money(stats.get("revenue", 0))),
            "🧾 Середній чек: <b>{}</b>".format(cards.money(stats.get("avg_check", 0))),
            "📈 Конверсія: <b>{:.1f}%</b>".format(stats.get("conversion", 0.0)),
            "❌ Частка скасувань: <b>{:.1f}%</b>".format(stats.get("cancel_rate", 0.0)),
        ]
    )

    reasons = stats.get("cancel_reasons") or []
    if reasons:
        lines.append("━━━━━━━━━━━━━━")
        lines.append("Причини скасувань:")
        for reason, count in reasons:
            lines.append("• {} — {}".format(cards.e(reason), count))

    return "\n".join(lines)
