# PickLoot 사이트

애드센스 + 아마존 어소시에이트 제휴 블로그용 Astro 정적 사이트입니다. 글은 마크다운 파일로 관리하고, 빌드하면 정적 HTML로 나와서 어디든 무료로 호스팅할 수 있습니다.

## 로컬에서 미리보기

```bash
npm install
npm run dev
```

`http://localhost:4321` 에서 확인할 수 있습니다.

## 새 글 추가하는 방법

`src/content/posts/` 폴더에 `.md` 파일을 하나 추가하면 자동으로 사이트에 반영됩니다. 예시(`best-portable-blenders-2026.md`)를 복사해서 아래 형식대로 채우면 됩니다.

```md
---
title: "글 제목"
description: "검색결과에 보일 요약 (1~2문장)"
publishDate: 2026-08-01
category: "카테고리명"
draft: false
products:
  - name: "제품명"
    amazonUrl: "https://www.amazon.com/실제상품링크"
    price: "$29.99"
    pros:
      - "장점 1"
      - "장점 2"
    cons:
      - "단점 1"
---

본문 내용 (마크다운). 제품 비교, 실사용 시나리오 등을 자유롭게 작성.
```

`products` 목록에 넣은 제품은 본문 아래에 카드 형태(가격·장단점·구매 버튼)로 자동 표시됩니다.

## 배포 (Cloudflare Pages, 무료)

1. 이 프로젝트를 GitHub 저장소에 올립니다.
   ```bash
   git init
   git add .
   git commit -m "Initial site"
   git branch -M main
   git remote add origin <본인의 GitHub 저장소 URL>
   git push -u origin main
   ```
2. [Cloudflare 대시보드](https://dash.cloudflare.com) → **Workers & Pages** → **Create application** → **Pages** → **Connect to Git** 에서 방금 만든 저장소를 선택합니다.
3. 빌드 설정:
   - Build command: `npm run build`
   - Build output directory: `dist`
4. 배포가 끝나면 `*.pages.dev` 임시 주소가 생깁니다.

## 도메인(pickloot.com, 가비아 등록) 연결하기

1. Cloudflare 대시보드에서 방금 만든 Pages 프로젝트 → **Custom domains** → `pickloot.com` 추가.
2. Cloudflare가 안내하는 네임서버 2개(예: `xxx.ns.cloudflare.com`)를 확인합니다.
3. 가비아 관리 화면 → 해당 도메인 → **네임서버 변경**에서 그 2개로 교체합니다.
4. 반영까지 몇 시간~24시간 정도 걸릴 수 있습니다. 완료되면 pickloot.com으로 접속됩니다.

## 애드센스 연결 전 체크리스트

- [ ] 실제 콘텐츠 15~25개 이상 채우기 (지금 있는 블렌더 글은 템플릿 확인용 샘플이므로 실제 글로 교체/추가 필요)
- [ ] `src/pages/contact.astro` 의 `hello@pickloot.com` 이 실제로 수신되는 주소인지 확인 — Cloudflare **Email Routing**(무료)으로 이 주소를 본인 Gmail로 포워딩 설정 가능
- [ ] `src/pages/privacy-policy.astro`, `disclaimer.astro` 의 "Last updated" 날짜를 실제 게시일로 수정
- [ ] 애드센스 계정에서 새 사이트(pickloot.com) 추가 → 소유권 확인 → 승인 대기
- [ ] 승인 후, `src/layouts/Layout.astro` 안의 주석 처리된 애드센스 스크립트에 실제 `ca-pub-XXXXXXXXXXXXXXXX` 코드를 넣고 주석 해제
- [ ] `public/ads.txt` 파일을 추가하고 애드센스가 알려주는 퍼블리셔 ID를 넣기 (지금은 아직 안 만들어 둔 상태)

## 폴더 구조

```
src/
  components/       Header, Footer, ProductCard
  content/posts/    글 (마크다운)
  content.config.ts 글 데이터 스키마
  layouts/Layout.astro   공통 레이아웃 (SEO 메타태그 포함)
  pages/            index, about, contact, privacy-policy, disclaimer, blog/[slug]
  styles/global.css 전체 스타일 (심플·가독성 중심)
```
