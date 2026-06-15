import { useEffect, useState } from 'react';
import { MapPin } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { resolveMunicipio, fetchPiramide, PORTE_LABEL, type Municipio, type PiramideItem } from '../../lib/ibgeApi';
import { formatNumber } from '../../lib/formatters';

interface Props {
  city?: string;
  state?: string;
}

export function IbgeMarketPanel({ city, state }: Props) {
  const [mun, setMun] = useState<Municipio | null>(null);
  const [pyramid, setPyramid] = useState<PiramideItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!city || !state) return;
    setLoading(true);
    setError(null);
    resolveMunicipio(city, state)
      .then((m) => {
        setMun(m);
        return fetchPiramide(m.id);
      })
      .then((p) => setPyramid(p.data))
      .catch(() => setError('Não foi possível obter dados do IBGE para esta cidade.'))
      .finally(() => setLoading(false));
  }, [city, state]);

  if (!city || !state) {
    return (
      <div className="bg-card rounded-xl shadow-sm border border-line border-dashed p-6">
        <div className="flex items-center gap-2 mb-1">
          <MapPin className="w-5 h-5 text-subtle" />
          <h2 className="text-lg font-bold text-ink">Mercado da região (IBGE)</h2>
        </div>
        <p className="text-sm text-muted">
          Preencha <strong>cidade</strong> e <strong>UF</strong> deste cliente (botão <strong>Editar</strong> acima) para ver população, porte do município e a pirâmide etária da região.
        </p>
      </div>
    );
  }

  const chartData = pyramid.map((p) => ({
    faixa: p.faixa,
    homens: -p.homens,
    mulheres: p.mulheres,
  }));

  return (
    <div className="bg-card rounded-xl shadow-sm border border-line p-6">
      <div className="flex items-center gap-2 mb-1">
        <MapPin className="w-5 h-5 text-brand" />
        <h2 className="text-lg font-bold text-ink">Mercado da região (IBGE)</h2>
      </div>
      <p className="text-sm text-muted mb-5">Contexto demográfico de {city}/{state} para calibrar público-alvo.</p>

      {loading && <div className="text-sm text-subtle">Carregando dados do IBGE...</div>}
      {error && <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">{error}</div>}

      {mun && !loading && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
            <div className="p-4 rounded-lg bg-base border border-line">
              <div className="text-xs text-muted mb-1">População</div>
              <div className="font-semibold text-ink">{formatNumber(mun.populacao)}{mun.populacao_ano ? ` (${mun.populacao_ano})` : ''}</div>
            </div>
            <div className="p-4 rounded-lg bg-base border border-line">
              <div className="text-xs text-muted mb-1">Porte do município</div>
              <div className="font-semibold text-ink">
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-brand/10 text-brand mr-2">{mun.classificacao_porte || '—'}</span>
                {mun.classificacao_porte ? PORTE_LABEL[mun.classificacao_porte] : ''}
              </div>
            </div>
            <div className="p-4 rounded-lg bg-base border border-line">
              <div className="text-xs text-muted mb-1">Município</div>
              <div className="font-semibold text-ink">{mun.nome}/{mun.uf_sigla}</div>
            </div>
          </div>

          {chartData.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-ink mb-2">Pirâmide etária (Censo IBGE)</h3>
              <div className="flex justify-center gap-8 text-xs text-muted mb-2">
                <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-sky-500 inline-block" /> Homens</span>
                <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-brand inline-block" /> Mulheres</span>
              </div>
              <div className="h-96 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} layout="vertical" stackOffset="sign" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
                    <XAxis type="number" tickFormatter={(v) => formatNumber(Math.abs(v))} tick={{ fontSize: 11, fill: '#9aa1b4' }} />
                    <YAxis type="category" dataKey="faixa" width={44} tick={{ fontSize: 11, fill: '#9aa1b4' }} reversed />
                    <Tooltip
                      formatter={(v: number, name: string) => [formatNumber(Math.abs(v)), name === 'homens' ? 'Homens' : 'Mulheres']}
                      contentStyle={{ borderRadius: '8px', border: '1px solid #e7e9f2', background: '#ffffff', color: '#1a1f36' }}
                    />
                    <Bar dataKey="homens" stackId="a">
                      {chartData.map((_, i) => <Cell key={i} fill="#0ea5e9" />)}
                    </Bar>
                    <Bar dataKey="mulheres" stackId="a">
                      {chartData.map((_, i) => <Cell key={i} fill="#ec298f" />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
