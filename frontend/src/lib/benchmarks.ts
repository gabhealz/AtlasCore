// Benchmarks de performance do funil — baseados no Doc 3 "Métricas e KPIs" da Healz.
// Servem para diagnosticar (verde/amarelo/vermelho) em qual etapa do funil está o gargalo.

export type Health = 'green' | 'yellow' | 'red' | 'neutral';

export interface Diag {
  status: Health;
  label: string;
  ideal: string;
}

function band(
  value: number | null | undefined,
  greenThreshold: number,
  yellowThreshold: number,
  higherIsBetter = true,
): Health {
  if (value == null || isNaN(Number(value))) return 'neutral';
  const v = Number(value);
  if (higherIsBetter) {
    if (v >= greenThreshold) return 'green';
    if (v >= yellowThreshold) return 'yellow';
    return 'red';
  }
  if (v <= greenThreshold) return 'green';
  if (v <= yellowThreshold) return 'yellow';
  return 'red';
}

type Metric = number | null | undefined;

// Cada função recebe o valor da métrica e devolve o diagnóstico segundo o Doc 3.
export const benchmarks = {
  ctr: (v: Metric): Diag => ({
    status: band(v, 5, 2),
    label: 'CTR',
    ideal: '5–10% no Google · 1–2,5% na Meta',
  }),
  cpc: (v: Metric): Diag => ({
    status: band(v, 3, 6, false),
    label: 'CPC',
    ideal: 'R$ 1,50–3,00 (cidades médias) · R$ 3–6 (grandes centros)',
  }),
  lp_to_whatsapp_rate: (v: Metric): Diag => ({
    status: band(v, 15, 10),
    label: 'Conversão do site (→ WhatsApp)',
    ideal: '> 20% excelente · 15–20% bom · 10–15% atenção · < 10% crítico',
  }),
  whatsapp_to_booking_rate: (v: Metric): Diag => ({
    status: band(v, 20, 15),
    label: 'WhatsApp → Agendamento',
    ideal: '> 30% excelente · 20–30% bom · 15–20% atenção · < 15% crítico',
  }),
  cost_per_conversion: (v: Metric): Diag => ({
    status: band(v, 15, 40, false),
    label: 'Custo por lead',
    ideal: 'R$ 10–15 (cidades médias) · até R$ 40 (grandes centros)',
  }),
};

export function healthClasses(status: Health): string {
  switch (status) {
    case 'green':
      return 'text-emerald-700 bg-emerald-50 border-emerald-200';
    case 'yellow':
      return 'text-amber-700 bg-amber-50 border-amber-200';
    case 'red':
      return 'text-rose-700 bg-rose-50 border-rose-200';
    default:
      return 'text-muted bg-elevated border-line';
  }
}

export function healthDot(status: Health): string {
  switch (status) {
    case 'green':
      return 'bg-emerald-500';
    case 'yellow':
      return 'bg-amber-500';
    case 'red':
      return 'bg-rose-500';
    default:
      return 'bg-subtle';
  }
}
