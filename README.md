#  CodeBuddy: AWS Bedrock 기반 GitHub PR 자동 리뷰어

AWS Bedrock(Claude 3 Haiku)과 Lambda를 활용하여 GitHub Pull Request가 생성/재오픈될 때 자동으로 PEP8 스타일 가이드 및 OWASP Top 10 기준 코드 리뷰를 수행하고, GitHub 댓글 및 Slack 알림을 전송하는 서버리스 인프라 아키텍처입니다.

##  프로젝트 폴더 구조
- `cloudformation/`: 인프라 자동 배포를 위한 CloudFormation 템플릿
- `docs/`: API 명세서 (Swagger/OpenAPI)
- `lambda/`: 백엔드 로직 (Orchestrator 및 GitHub 도구 람다)
- `tests/`: 시연 및 검증용 샘플 파이썬 코드 (`app.py`)

##  설치 및 배포 방법 (Installation)
1. `cloudformation/template.yaml` 파일을 AWS CloudFormation에 업로드하여 스택을 배포합니다.
2. 배포 시 매개변수(Parameters) 입력창에 본인의 `AgentId`, `AliasId`, `GitHubToken`, `SlackWebhookUrl`을 입력합니다.
3. 배포가 완료되면 `Outputs` 탭에서 생성된 **ApiGatewayInvokeUrl**을 복사합니다.
4. 대상 GitHub 저장소 설정(Settings) -> Webhooks 메뉴로 이동하여 복사한 URL을 Payload URL에 등록합니다. (Content type: `application/json`, 이벤트: `Pull requests`)

##  사용법 (Usage)
1. GitHub 저장소에서 새로운 기능 브랜치를 생성하고 `tests/app.py` 코드를 수정 후 커밋합니다.
2. `main` 브랜치를 대상으로 **Pull Request를 생성(Open)하거나 재오픈(Reopen)** 합니다.
3. 봇(CodeBuddy)이 자동으로 구동되어 구조화된 리뷰 댓글을 남기고 슬랙 채널로 알림 메시지를 전송합니다.
