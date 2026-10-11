# 2026-10-11 solusupport-bot 계정의 GitHub Actions가 정지돼 있어서(land-in-korea와 동일 원인)
# telegram-notify.yml / bluesky-post.yml이 돌지 않는다. 같은 스크립트를 이 PC에서 직접 실행한다.
#   -Mode telegram : 15분마다 (작업 스케줄러 PickLootSite-TelegramNotify)
#   -Mode bluesky  : 하루 6회 (작업 스케줄러 PickLootSite-BlueskyPost)
# 시크릿은 저장소 루트 .env에서 읽는다(.gitignore에 이미 포함됨, 값이 없으면 각 파이썬
# 스크립트가 스스로 "not set — skipping"으로 안전하게 종료한다).
param([ValidateSet('telegram', 'bluesky')][string]$Mode = 'telegram')

$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$logFile = Join-Path $PSScriptRoot "run-local.log"
function Log($msg) { Add-Content -Path $logFile -Value "$(Get-Date -Format o) [$Mode] $msg" -Encoding utf8 }

# 텔레그램/블루스카이 두 모드가 겹쳐 돌면 같은 저장소에 동시에 git add/commit/push를
# 하게 된다 — 한 번에 하나만.
$mutex = New-Object System.Threading.Mutex($false, "Global\PickLootSiteCron")
if (-not $mutex.WaitOne([TimeSpan]::FromMinutes(10))) { Log "SKIP: 이전 실행이 아직 진행 중"; exit 0 }

try {
    Set-Location $repo
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    # credential.helper가 인증을 다시 물어야 하는 상황이면 무인 실행에서 프롬프트가
    # 뜰 사람이 없어 git 프로세스가 영원히 멈춰버린다 — 실패시키고 넘어가게 한다.
    $env:GIT_TERMINAL_PROMPT = '0'
    # 작업 스케줄러(숨김 창, 콘솔 미연결)에서 돌면 파이썬 stdout이 UTF-8이 아니라
    # 시스템 ANSI 코드페이지(cp949)로 떨어져서 "—" 같은 문자를 print()하다 그대로
    # UnicodeEncodeError로 죽는다 — 강제로 UTF-8 모드를 쓰게 한다.
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'

    # .env를 환경변수로 주입 (KEY=VALUE, '#'으로 시작하는 줄과 빈 줄은 무시)
    $envFile = Join-Path $repo ".env"
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            $line = $_.Trim()
            if ($line -eq '' -or $line.StartsWith('#')) { return }
            $idx = $line.IndexOf('=')
            if ($idx -lt 1) { return }
            $key = $line.Substring(0, $idx).Trim()
            $val = $line.Substring($idx + 1).Trim()
            [System.Environment]::SetEnvironmentVariable($key, $val, 'Process')
        }
    }

    git pull -q --rebase --autostash origin main 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        git rebase --abort 2>&1 | Out-Null
        Log "FAIL: 실행 전 git pull 실패 — 작업 트리가 깨끗하지 않을 수 있습니다. 이번 실행을 건너뜁니다."
        return
    }

    if ($Mode -eq 'telegram') {
        $script = 'scripts/post_to_telegram.py'
        $queuePath = 'notify/telegram'
        $commitMsg = 'chore: mark Telegram notification(s) as sent'
    } else {
        $script = 'scripts/post_to_bluesky.py'
        $queuePath = 'social/bluesky'
        $commitMsg = 'chore: mark Bluesky post as sent'
    }

    $out = & python $script 2>&1 | Out-String
    Add-Content -Path $logFile -Value $out -Encoding utf8
    if ($LASTEXITCODE -ne 0) { Log "FAIL: $script (exit $LASTEXITCODE)" } else { Log "OK: $script" }

    git diff --quiet -- $queuePath
    if ($LASTEXITCODE -ne 0) {
        git add -- $queuePath
        git commit -q -m $commitMsg -- $queuePath
        Log "commit: $commitMsg"
    }

    git push -q origin main 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Log "WARN: git push 실패 — 원격에 새 커밋이 있을 수 있음, 다음 실행에서 pull 후 재시도됨" }
} finally {
    $mutex.ReleaseMutex()
}
