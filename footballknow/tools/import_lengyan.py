"""Import the ten public-domain volumes, preserving source text and provenance."""
import hashlib
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1] / 'public' / 'jingzang'
NUMBERS = '一二三四五六七八九十'


def main():
    chapters, sources, titles = [], [], []
    for number, chinese in enumerate(NUMBERS, 1):
        url = 'https://zh.wikisource.org/wiki/' + urllib.parse.quote(f'楞嚴經/卷{number:02}')
        request = urllib.request.Request(url, headers={'User-Agent': 'JingzangTextImport/1.0 (https://tripitaka.shop/)'})
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read()
        soup = BeautifulSoup(raw, 'html.parser')
        content = soup.select_one('.mw-parser-output')
        paragraphs = []
        for node in content.find_all(recursive=False):
            if node.name == 'p':
                paragraphs.append(re.sub(r'\s+', '', node.get_text()))
            elif node.name == 'dl':
                paragraphs.extend(re.sub(r'\s+', '', line) for line in node.get_text().splitlines() if line.strip())
        assert paragraphs[0] == f'楞嚴經卷{chinese}', f'Unexpected heading: {number}'
        paragraphs = [p for p in paragraphs[1:] if p and not re.fullmatch(r'大佛頂如來密因修證了義諸菩薩萬行首楞嚴經卷第[一二三四五六七八九十]+', p)]
        # No verse or mantra block may silently disappear outside paragraph elements.
        other = [node for node in content.find_all(recursive=False) if node.name not in {'p', 'dl', 'div', 'style', 'table', 'link'} and node.get_text(strip=True)]
        assert not other, f'Unreviewed content elements: {number}'
        text = ''.join(paragraphs)
        assert len(text) > 4500 and '阿難' in text, f'Incomplete volume: {number}'
        permalink = urllib.parse.urljoin(url, soup.select_one('#t-permalink a')['href'])
        chapters.append({'p': paragraphs})
        titles.append({'t': f'卷第{chinese}', 'sourceUrl': permalink})
        sources.append({'volume': number, 'url': url, 'permalink': permalink,
                        'sourceSha256': hashlib.sha256(raw).hexdigest(),
                        'textSha256': hashlib.sha256(text.encode()).hexdigest(),
                        'paragraphs': len(paragraphs), 'charactersWithPunctuation': len(text),
                        'start': text[:32], 'end': text[-64:]})
        print(f'Volume {number}: {len(paragraphs)} paragraphs, {len(text)} characters', flush=True)
    assert chapters[0]['p'][0].startswith('如是我聞')
    assert '作禮而去' in chapters[-1]['p'][-1]
    assert '南無' in ''.join(chapters[6]['p']) and len(chapters[6]['p']) > 100
    metadata = {'id': 'lyj', 'name': '楞严经', 'full': '大佛顶首楞严经', 'cat': '佛',
                'tradition': 'hanchuan', 'unit': '卷', 'by': '唐 · 般剌蜜帝 译（经本题署）',
                'intro': '全称《大佛顶如来密因修证了义诸菩萨万行首楞严经》，全十卷。由阿难问法展开，论心性、圆通与修行次第；卷七收楞严神咒，卷九、卷十辨五阴境界。',
                'src': '维基文库《楞嚴經》十卷电子本，原文保留底本字形与标点。只移除卷首导航、卷末重复书名和网页空白，未附现代讲解。每卷提供固定版本链接。',
                'sourceUrl': 'https://zh.wikisource.org/wiki/楞嚴經', 'sourceLabel': '查看经文来源',
                'licenseUrl': 'https://creativecommons.org/licenses/by-sa/4.0/deed.zh-hans',
                'licenseLabel': '古籍正文属公版；电子整理文本署名维基文库贡献者，依 CC BY-SA 4.0 分享。',
                'chars': len(re.findall(r'[\u3400-\u9fff\U00020000-\U000323af]', ''.join(''.join(c['p']) for c in chapters))),
                'plain': 0, 'ch': titles}
    catalogue_path = ROOT / 'index.json'
    catalogue = json.loads(catalogue_path.read_text('utf-8'))
    catalogue = [b for b in catalogue if b['id'] != 'lyj']
    catalogue.insert(next(i for i, b in enumerate(catalogue) if b['id'] == 'jgj') + 1, metadata)
    for book in catalogue:
        if book['cat'] == '佛' or book.get('of') in {'xj', 'jgj'}:
            book['tradition'] = 'hanchuan'
    (ROOT / 'books' / 'lyj.json').write_text(json.dumps(chapters, ensure_ascii=False, separators=(',', ':')) + '\n', 'utf-8')
    catalogue_path.write_text(json.dumps(catalogue, ensure_ascii=False, separators=(',', ':')) + '\n', 'utf-8')
    (ROOT / 'lengyan-sources.json').write_text(json.dumps({'book': 'lyj', 'volumes': sources}, ensure_ascii=False, indent=2) + '\n', 'utf-8')


if __name__ == '__main__':
    main()
