// Local OFL fonts loaded through the FontFace API (never relies on system fonts for type).
const FACES: [string, string, FontFaceDescriptors][] = [
  ['Instrument Serif', 'InstrumentSerif-Italic.ttf', { style: 'italic' }],
  ['Instrument Serif', 'InstrumentSerif-Regular.ttf', { style: 'normal' }],
  ['Inter Tight', 'InterTight[wght].ttf', { weight: '100 900', style: 'normal' }],
  ['Inter Tight', 'InterTight-Italic[wght].ttf', { weight: '100 900', style: 'italic' }],
  ['Plex Mono', 'IBMPlexMono-Regular.ttf', { weight: '400' }],
  ['Plex Mono', 'IBMPlexMono-Medium.ttf', { weight: '500' }],
  ['Plex Mono', 'IBMPlexMono-SemiBold.ttf', { weight: '600' }],
  ['Courier Prime', 'CourierPrime-Regular.ttf', { weight: '400' }],
  ['Courier Prime', 'CourierPrime-Bold.ttf', { weight: '700' }],
  ['Special Elite', 'SpecialElite-Regular.ttf', { weight: '400' }],
];
export async function loadFonts(base = 'assets/fonts/') {
  await Promise.all(FACES.map(async ([fam, file, desc]) => {
    const f = new FontFace(fam, `url("${base}${encodeURIComponent(file)}")`, desc);
    await f.load(); (document as any).fonts.add(f);
  }));
  // CJK seal/label glyphs come from the system Noto CJK family (OFL), warmed up here.
  await (document as any).fonts.load('700 64px "Noto Serif CJK SC"', '假公安吉林');
}
export const F = { serif: 'Instrument Serif', sans: 'Inter Tight', mono: 'Plex Mono', type: 'Courier Prime', elite: 'Special Elite', cjk: 'Noto Serif CJK SC', cjkSans: 'Noto Sans CJK SC' };
