# PPTX Convert

PowerPoint (`.pptx`) dosyalarını, şekil ve bağlantı semantiğini mümkün olduğunca koruyan bir AST/JSON yapısına dönüştürür ve bu AST'yi React Flow tabanlı bir canvas üzerinde gösterir.

Projenin amacı yalnızca slaytı görsel olarak yeniden çizmek değildir. Bir PPTX içindeki dikdörtgen, elips, karar elması, grup, resim, tablo ve bağlayıcı ok gibi nesnelerin türünü; konum, boyut, döndürme, flip, metin, renk, çizgi ve bağlantı uçlarıyla birlikte React tarafına taşımaktır.

## Çalışma akışı

```text
data/input/example.pptx
        |
        | npm run convert
        v
data/output/example.json
        |
        | Vite import
        v
React Flow canvas
```

1. `src/python/main.py`, PresentationML içeriğini `python-pptx` ve `lxml` ile okur.
2. Derleyici slaytları, şekilleri, resimleri, tabloları ve bağlayıcıları `LiveCanvasDeckAST` yapısına dönüştürür.
3. AST JSON olarak `data/output/example.json` dosyasına yazılır.
4. `src/App.tsx`, bu güncel JSON çıktısını import eder.
5. `src/LiveCanvasViewer.tsx`, AST düğümlerini ve kenarlarını React Flow üzerinde gösterir.

## Klasör yapısı

```text
PPTX_CONVERT/
├── data/
│   ├── input/
│   │   └── example.pptx       # Dönüştürülecek örnek PPTX
│   └── output/
│       └── example.json       # Derleyicinin ürettiği AST JSON
├── src/
│   ├── python/
│   │   └── main.py            # PPTX -> AST JSON derleyicisi
│   ├── App.tsx                # JSON AST'yi uygulamaya bağlar
│   ├── LiveCanvasViewer.tsx   # AST -> React Flow görüntüleyici
│   ├── main.tsx               # React uygulama başlangıç noktası
│   ├── types.ts               # AST ve canvas TypeScript tipleri
│   └── index.css              # Global canvas stilleri
├── index.html                 # Vite HTML giriş dosyası
├── package.json               # Komutlar ve bağımlılıklar
├── tsconfig.app.json          # Uygulama TypeScript ayarları
├── tsconfig.node.json         # Vite yapılandırması TypeScript ayarları
├── vite.config.ts             # Vite yapılandırması
└── eslint.config.js           # ESLint yapılandırması
```

`src/` altında PPTX veya derleme çıktısı tutulmaz. Girdi ve çıktı dosyaları `data/input/` ve `data/output/` altında ayrıdır.

> Not: Çalışma alanında daha önce açılmış olan `src/example.pptx` ve `src/~$example.pptx`
> dosyaları Windows/VS Code tarafından kilitli eski dosya artıkları olarak görünebilir.
> Uygulama ve `npm run convert` bu dosyaları kullanmaz; aktif girdi yalnızca
> `data/input/example.pptx` dosyasıdır. Dosyalar kilitleri kaldırıldıktan sonra güvenle silinebilir.

## Gereksinimler

- Node.js ve npm
- Python 3
- Python paketleri:
  - `python-pptx`
  - `lxml`

Python paketlerini kurmak için:

```powershell
python -m pip install python-pptx lxml
```

JavaScript bağımlılıklarını kurmak için:

```powershell
npm install
```

## Komutlar

### PPTX -> JSON

```powershell
npm run convert
```

Bu komut aşağıdaki örnek dosyaları kullanır:

- Girdi: `data/input/example.pptx`
- Çıktı: `data/output/example.json`

Derleyiciyi doğrudan farklı dosyalarla çalıştırmak için:

```powershell
python src/python/main.py <girdi.pptx> <çıktı.json>
```

Örnek:

```powershell
python src/python/main.py data/input/example.pptx data/output/example.json
```

### Geliştirme sunucusu

```powershell
npm run dev
```

Vite geliştirme sunucusunu başlatır. Uygulama, `src/App.tsx` içindeki `../data/output/example.json` importuyla derlenmiş AST'yi açar. Yeni PPTX üzerinde değişiklik yaptıktan sonra önce `npm run convert` çalıştırılmalıdır.

### Production build

```powershell
npm run build
```

TypeScript kontrolünü çalıştırır ve Vite production çıktısını `dist/` klasörüne üretir.

### Lint

```powershell
npm run lint
```

TypeScript/React kaynaklarında ESLint kontrolü yapar.

### Production önizleme

```powershell
npm run preview
```

Önceden oluşturulmuş Vite build'ini yerel olarak sunar.

## AST modeli

Derleyicinin temel çıktısı `LiveCanvasDeckAST` tipidir:

- `presentation`: slayt boyutu ve tema fontları
- `slides`: slayt listesi
- `nodes`: şekil, resim, tablo ve sanal anchor düğümleri
- `edges`: PPTX bağlayıcıları ve bağlantı uçları

Şekil düğümleri `shapePreset` alanında PPTX geometrisini taşır. Geometri; `x`, `y`, `width`, `height`, `rotation`, `flipH` ve `flipV` alanlarını içerir. Bağlayıcılar kaynak/hedef düğüm kimliklerini, portlarını, çizgi stilini ve başlangıç/bitiş ok uçlarını korur.

React görüntüleyici, dikdörtgen olmayan şekilleri SVG polygon olarak çizer; böylece karar elması, üçgen, ok ve benzeri şekiller düz bir dikdörtgene indirgenmez. Bağlayıcılar da AST'deki kaynak/hedef portlarına bağlanır.

## Yeni PPTX dönüştürme

1. Dönüştürülecek dosyayı `data/input/` içine koyun.
2. `package.json` içindeki `convert` komutunu yeni dosya adlarına göre güncelleyin veya Python derleyicisini doğrudan çağırın.
3. `npm run convert` çalıştırın.
4. Oluşan JSON'un `src/App.tsx` tarafından import edildiğini kontrol edin.
5. `npm run dev` ile canvas'ı açın.

## Doğrulama

Önerilen kontrol sırası:

```powershell
npm run convert
npm run lint
npm run build
```

`npm run convert` başarılı olduğunda slayt sayısını terminalde bildirir ve JSON dosyasını `data/output/` içine yazar.

## Bilinen sınırlar

- `npm run convert` şu anda örnek dosya adlarını sabit kullanır; kullanıcı arayüzünden dosya seçimi yoktur.
- PPTX'teki her ileri seviye Office özelliği React Flow karşılığına sahip olmayabilir.
- `dist/` build çıktısıdır; kaynak AST ve PPTX dosyalarının yerine geçmez.

## Bilinen sorunlar / eklenmesi gerekenler

- Fontlar aktarılmıyor.
- Oklar içi boş dikdörtgen olarak geçiriliyor.
- Arka plan rengi veya herhangi bir arka plan beyaz kısımlarda bulunmuyor
- Dinamiki ve playground benzeri yapısı var, daha strict ve ders ortamı şekline sokulması lazım.