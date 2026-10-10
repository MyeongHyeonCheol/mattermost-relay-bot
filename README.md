# Mattermost 팀장 공지 전달 봇

팀장 전용 비공개 채널의 지정 발신자 글·첨부를 5분마다 폴링해 대상 채널에 복사 전달합니다.
(봇 계정·토큰 발급이 막힌 서버에서, 본인 계정으로 로그인해 동작하는 self-bot 방식)

## 동작 방식
1. 본인 계정으로 로그인(세션 토큰).
2. 각 소스 채널에서 `state.json`의 마지막 처리 시각 이후 글 조회.
3. 발신자가 `allowed_senders`에 포함된 글만 필터(시스템 글 제외, 시간순 정렬).
4. 머리말 + 원문 + 첨부(다운로드 후 재업로드)를 대상 채널에 게시.
5. 처리 지점을 `state.json`에 저장(중복 방지).

## 설정
1. `config.example.yaml` → `config.yaml` 복사 후 채널/발신자 입력.
2. 자격증명 — 둘 중 하나:
   - **`.env` 파일**(권장): `.env.example` → `.env` 복사 후 `MM_LOGIN_ID`/`MM_PASSWORD` 입력.
     봇 실행 시 자동으로 읽습니다. (`.env`는 `.gitignore`에 있어 GitHub에 안 올라감)
   - 또는 환경변수 직접 설정: `$env:MM_LOGIN_ID=...; $env:MM_PASSWORD=...` (그 터미널에서만 유효).
   - 둘 다 있으면 **환경변수가 `.env`보다 우선**합니다.
3. 로컬 테스트: `python -m bot.main` (처음엔 `dry_run: true`).
4. 멤버 username 확인: `python -m bot.list_members "채널표시이름"`.

> Windows(conda) 예: `C:\Users\SSAFY\miniforge3\python.exe -m bot.main`

## 로컬 검증 순서
1. `dry_run: true`로 1회 실행 → 첫 실행이면 `[baseline]`만 출력(전달 없음).
   드라이런도 기준선/진행 지점을 `state.json`에 **저장**하므로 다음 실행이 이어집니다.
2. 소스 채널에 글을 올린 뒤 다시 실행 → `[DRY-RUN]` 로그로 전달 예정 내용 확인.
3. `dry_run: false`로 바꿔 실제 전달 확인(재실행 시 중복 없어야 함).

> 참고: 드라이런도 상태를 전진시키므로, 같은 글을 반복 미리보기하려면 `state.json`을 되돌리거나 새 글을 올리세요.

## GitHub Actions (무료, PC 꺼도 동작)
- **공개** 저장소로 push (Actions 무제한 무료).
- 저장소 Settings → Secrets and variables → Actions 에
  `MM_LOGIN_ID`, `MM_PASSWORD`, `MM_DEST_CHANNEL_ID`(대상 채널 ID) 등록. (코드엔 절대 넣지 않음)
- **`config.yaml`과 초기 `state.json`을 반드시 커밋**해야 합니다. 그렇지 않으면
  Actions 실행기가 설정을 찾지 못하거나(없으면 즉시 오류), 매번 기준선만 다시 잡아
  아무것도 전달하지 못합니다. 초기 `state.json`은 로컬에서 1회 실행해 생성한 뒤 커밋하세요.
- `.github/workflows/relay.yml`이 5분마다 실행하며, `state.json`이 바뀌면 커밋·푸시합니다.

## 테스트 → 운영 전환
`config.yaml`의 값만 교체:
- `source_channels`: `"[자율 2반] 팀장"`, `"<팀장채널>"`
- 대상 채널 ID: Secrets/`.env`의 `MM_DEST_CHANNEL_ID`
  - 지정하면 이름 조회 없이 그 ID로 전달합니다. 없으면 `destination_channel` 표시 이름으로 찾습니다.
- `allowed_senders`: 4명(장나현·허수민·이현석·조하원) + 본인

## 주의
- GitHub 실행기는 해외 IP라 반복 로그인이 보안 감지될 수 있음.
- cron은 지연/건너뜀 가능(실시간 아님). 60일 무활동 시 예약 자동 중지.
- 비공개 채널을 자동 접근하는 self-bot이므로, 서버 운영 정책을 확인하고 사용할 것.
