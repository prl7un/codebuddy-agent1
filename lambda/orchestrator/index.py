import json
import os
import boto3
import uuid
import urllib.request
import urllib.parse

def handler(event, context):
    sts = boto3.client('sts')
    identity = sts.get_caller_identity()
    print(f"현재 람다가 사용 중인 ARN: {identity['Arn']}")  
    print("Received event:", json.dumps(event))
    try:
        body = json.loads(event.get('body', '{}'))

        # GitHub Webhook의 세부 액션(opened, reopened, closed 등) 추출
        pr_action = body.get('action', '') 

        # opened 또는 reopened 상태가 아니라면(예: closed) 에이전트를 호출하지 않고 즉시 종료
        if pr_action not in ['opened', 'reopened']:
            print(f"리뷰 대상이 아닌 이벤트(Action: {pr_action})이므로 작업을 건너뜁니다.")
            return {
                "statusCode": 200,
                "body": json.dumps({"message": f"Event ignored: {pr_action}", "status": "ignored"})
            }

        
        # 1. 깃허브 Webhook에서 PR URL 추출
        pr_url = body.get('pull_request', {}).get('html_url', body.get('pr_url'))

        # [보안 강화 1] URL 유효성 검사 (아무 값이나 프롬프트에 들어가지 못하도록 방지)
        if not pr_url or not str(pr_url).startswith("https://github.com/"):
            return {"statusCode": 200, "body": json.dumps({"message": "Not a valid GitHub PR event"})}
            
        # 복잡한 Webhook JSON 구조에서 람다가 직접 파라미터 4개를 미리 안전하게 추출합니다.
        owner = body.get('repository', {}).get('owner', {}).get('login', '')
        repo = body.get('repository', {}).get('name', '')
        pr_number = body.get('number', '')
        
        # 만약 웹훅 데이터 구조가 다를 경우를 대비한 URL 기반 2차 안전 파싱
        if not all([owner, repo, pr_number]):
            url_parts = pr_url.replace("https://github.com/", "").split("/")
            if len(url_parts) >= 4:
                owner = url_parts[0]
                repo = url_parts[1]
                pr_number = url_parts[3]

        # 2. 환경 변수에서 Agent ID, Alias ID, Slack Webhook URL 가져오기
        agent_id = os.environ.get('AGENT_ID')
        agent_alias_id = os.environ.get('ALIAS_ID')
        slack_webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
        
        if not agent_id or not agent_alias_id:
            raise ValueError("환경 변수 누락 (AGENT_ID 또는 ALIAS_ID)")

        # 3. Bedrock Agent Runtime 클라이언트 생성
        client = boto3.client(
            service_name='bedrock-agent-runtime', 
            region_name='ap-northeast-2'
        ) 
        
        # 4. Agent에게 내릴 명령(프롬프트) 작성 [Haiku 최적화 가이드라인 설계]
        friendly_prompt = f"""GitHub Pull Request 웹훅 이벤트가 감지되었습니다.
제공된 정보(owner: {owner}, repo: {repo}, pr_number: {pr_number})를 바탕으로 사용자의 소스 코드를 PEP8 및 OWASP 기준으로 즉시 분석하세요.

분석이 완료되면 **반드시 단 한 번만 'post_pr_1' 도구를 실행**하여 comment 파라미터에 댓글을 등록해야 합니다.

이때, 등록할 `comment` 파라미터의 내용은 반드시 아래 포맷을 엄격히 준수하여 작성하세요:

[댓글 포맷 가이드]
안녕하세요. CodeBuddy AI 프로그래밍 어시스턴트입니다. 제공된 GitHub PR을 분석한 결과, 코드 스타일 가이드 준수, 보안 취약점, 코드 복잡도 등에 대한 리뷰 의견을 남깁니다.

###   1. 코드 스타일 가이드 (PEP8) 리뷰
- (여기에 Haiku 너가 분석한 변수명 규칙, 들여쓰기 등 스타일 가이드 준수 여부와 개선점을 적으세요.)

###   2. 보안 취약점 (OWASP Top 10) 리뷰
- (여기에 실제 SQL 연동이 없다면 SQL 인젝션 오탐지를 하지 말고, 문자열 결합(+ str(user_id)) 로직에 대한 '파라미터 유효성 검증 부족' 또는 'URL 오염 위험' 관점으로 정확한 취약점과 수정 제안을 적으세요.)

###   3. 코드 복잡도 및 리팩토링 제안
- (여기에 displayUserInfo 및 process_and_print_and_save_data 함수의 로직 간소화 및 개선안을 적으세요.)

감사합니다.

다른 사족이나 대답은 절대 하지 말고, 위 포맷에 맞춰 본문 내용을 완성한 뒤 즉시 'post_pr_1' 도구를 실행하세요."""
        
        session_id = 'test-session-001'
        
        # 5. Agent 실행 (Invoke) - 수정된 프롬프트(friendly_prompt) 전달
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=friendly_prompt,
            enableTrace=True  # 디버깅을 위한 Trace 활성화
        )
        
        # 6. Agent의 응답 결과 수집
        completion = ""
        for event in response.get('completion'):
            if 'chunk' in event:
                chunk = event['chunk']
                completion += chunk['bytes'].decode('utf-8')

        print(f"Agent 응답 완료: {completion}")        

        # 7. [✨ 슬랙 알림 기능 추가 생성 섹션]
        # 오케스트레이터의 환경변수를 활용하여 백엔드 분석 완료 사실을 슬랙에 공유합니다.
        if slack_webhook_url:
            print("슬랙 알림 전송 시작...")
            slack_message = {
                "text": f"🚀 *CodeBuddy PR 자동 리뷰 완료*\n\n*대상 저장소:* {owner}/{repo}\n*PR 번호:* #{pr_number}\n*리뷰 상태:*성공적으로 GitHub에 댓글이 등록되었습니다.\n*PR 바로가기:* {pr_url}"
            }
            slack_data = json.dumps(slack_message).encode('utf-8')
            slack_req = urllib.request.Request(
                slack_webhook_url, 
                data=slack_data, 
                headers={'Content-Type': 'application/json'}, 
                method='POST'
            )
            try:
                with urllib.request.urlopen(slack_req) as slack_res:
                    print("슬랙 알림 전송 완료")
            except Exception as se:
                print(f"슬랙 발송 중 내부 에러(경고): {str(se)}")
        else:
            print("경고: 환경변수에 SLACK_WEBHOOK_URL이 설정되어 있지 않아 알림을 건너뜁니다.")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "리뷰 완료 및 댓글 작성 성공", "status": "success"})
        }
        
    except Exception as e:
        # [보안 강화 2] 서버 로그에는 실제 에러를 남기고 응답으로는 내부 정보(e)를 숨김
        print(f"Internal Error: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}
