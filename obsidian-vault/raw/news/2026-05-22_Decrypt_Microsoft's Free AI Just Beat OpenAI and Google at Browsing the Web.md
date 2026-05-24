---
url: "https://decrypt.co/368807/microsoft-fara15-open-source-ai-beats-openai-gemini"
source: "Decrypt"
category: "bitcoin"
published_at: "2026-05-22 20:31:03"
title: "마이크로소프트의 오픈소스 AI, 웹 브라우징 능력으로 OpenAI 및 구글 능가하며 시장 주목"
language: "ko"
tags: [azure ai foundry, ai agent, open-weight ai, bitcoin, fara1.5, enriched, microsoft research, news]
---

# 마이크로소프트의 오픈소스 AI, 웹 브라우징 능력으로 OpenAI 및 구글 능가하며 시장 주목

**작성 언론사**: Decrypt
**게시 일자**: 2026-05-22 20:31:03
**원문 주소**: https://decrypt.co/368807/microsoft-fara15-open-source-ai-beats-openai-gemini
**기사 언어**: ko

---

## 기사 본문 (AI 분석 요약)

최근 마이크로소프트 리서치(Microsoft Research)가 공개한 'Fara1.5' 모델이 웹 브라우징 및 에이전트(Agent) 기반 작업 수행 능력에서 OpenAI의 Operator와 구글의 Gemini 2.5 Computer Use를 능가하며 큰 주목을 받고 있습니다. 이 모델은 40억, 90억, 270억 개의 파라미터를 가진 오픈 웨이트(Open-Weight) 구조로, 특히 90억 파라미터 버전이 이미 Azure AI Foundry를 통해 공개되어 접근성이 높다는 장점이 있습니다. [[Bitcoin]] 시장의 주요 트렌드가 AI 기술 발전과 결합하면서, 이러한 오픈소스 AI의 성능 우위는 향후 [[US-Fed]]의 [[금리]] 정책이나 [[Korea-Economy]]의 디지털 전환 속도에 영향을 미칠 핵심 인프라로 간주됩니다.

Fara1.5의 핵심 강점은 단순히 지식을 나열하는 것을 넘어, 사용자가 마치 사람이 직접 하는 것처럼 웹사이트를 탐색하고, 여러 비교 사이트를 거쳐, 예약 양식을 작성하고, 최종 결제까지 완료하는 '컴퓨터 사용 에이전트' 역할을 수행한다는 점입니다. 이는 기존의 독점적이고 클라우드 기반의 AI 솔루션(OpenAI, Google)이 높은 비용과 폐쇄성이라는 한계를 가졌던 것과 대비됩니다. 특히, 마이크로소프트가 GPT-5.4와 같은 최신 모델을 '교사 에이전트'로 활용하여 학습 데이터를 생성하고, 가상 웹 환경(Synthetic Domain Training)에서 훈련시킨 방식은 모델의 실용성과 안정성을 극대화한 것으로 평가됩니다. 이러한 오픈소스 기반의 고성능 에이전트 AI는 향후 금융 서비스나 자산 관리 분야에서도 혁신적인 변화를 가져올 잠재력을 지니고 있습니다.

결론적으로, Fara1.5는 오픈소스 생태계 내에서 최고 수준의 웹 에이전트 성능을 입증하며, AI 기술의 민주화와 상업적 활용도를 동시에 높였다는 점에서 시장의 큰 관심을 받고 있습니다. 이는 향후 AI 기반의 자동화된 금융 거래나 정보 검색 서비스 시장의 경쟁 구도를 재편할 주요 동인이 될 것입니다. [[Bitcoin]] 투자자들은 이러한 기술적 진보가 금융 인프라 전반에 미치는 파급 효과를 면밀히 관찰할 필요가 있습니다.

---
<details><summary>📄 원문 보기</summary>

In brief

Fara1.5-27B scored 72% on Online-Mind2Web, beating OpenAI Operator (58.3%) and Gemini 2.5 Computer Use (57.3%).

The models are open-weight, come in 4 billion, 9 billion, and 27 billion parameter sizes, and are built on fine-tuned Qwen 3.5.

Fara1.5-9B is live now on Azure AI Foundry; 4B and 27B arrive shortly.

Imagine telling your computer to look up vacation rentals, compare five sites, fill out the booking form, and confirm the one closest to the beach. You go make coffee. It’s done when you get back. That is the promise of "computer use agents"—AI that reads your browser screen and clicks, scrolls, and types exactly as a human would, with no special plugins required.

OpenAI tried this first with Operator

, launched in January 2025 at $200 a month before being folded into ChatGPT Agent and shut down in August. Google has Gemini 2.5 Computer Use. Both are proprietary, cloud-based, and expensive to run.

This week, Microsoft Research released a tiny model named

Fara1.5

—and on the benchmarks that count, it beats them both.

The family comes in three sizes: 4 billion, 9 billion, and 27 billion parameters, all built on Qwen3.5, an Alibaba base model that Microsoft fine-tuned for browser work, with all weights publicly released. (Parameters are what determine an AI model's breadth of knowledge, with more generally meaning a higher capacity.)

Getting there required rethinking the whole development process from scratch. "We started with a simple question: What does it take to make a small model genuinely good at agentic tasks?" the AI Frontiers team

wrote

. "The answer spanned the full lifecycle—data generation, training objectives, model design, and orchestration had to be redesigned together rather than in isolation."

The benchmarks

Online-Mind2Web is the benchmark that matters in the task Microsoft wanted to excel. It tests how often an AI agent correctly completes 300 diverse, real-world tasks across 136 popular live websites—things like comparing products, filling forms, and booking services—scored as a percentage of tasks finished correctly on the actual, changing internet.

Fara1.5-27B scored 72%. OpenAI Operator scored 58.3%. Google's Gemini 2.5 Computer Use scored 57.3%. Yutori's Navigator n1, the top proprietary alternative, reached 64.7%. Even Fara1.5-9B, the mid-sized model, hit 63.4%—ahead of both OpenAI and Google.

Open-source rivals also fell short. Alibaba's GUI-Owl-1.5 at 8 billion parameters scored 48.6%. AI2's MolmoWeb scored 35.3%. Microsoft's own previous model, Fara-7B, scored 34.1%—making this release nearly double its predecessor at a comparable size.

On WebVoyager, a second benchmark measuring task success on the live web scored the same way, Fara1.5-27B hit 88.6%, edging OpenAI Operator's 87.0% and beating H Company's 30-billion-parameter Holo2 at 83.0%.

How it learned

The secret sauce is the training pipeline. Microsoft used a system called FaraGen1.5 to generate the training data. Here's the clever part: they used GPT-5.4—OpenAI's model—as a "teacher agent" to demonstrate how to complete browser tasks. Those demonstrations become the training data for Fara1.5. You're essentially using OpenAI's most capable model to train a rival open-source one.

They also created six fake, fully functional replicas of real websites—email clients, calendars, marketplaces—so the model could practice tasks that require logins or irreversible actions (like actually sending an email or booking a flight) without touching real accounts. That's called synthetic domain training, and it's a significant part of why Fara1.5 handles "gated" tasks better than its predecessors.

Every model is designed to stop and ask before doing something it cannot undo. "Balancing robust safeguards such as Critical Points with seamless user journeys is key," Yash Lara, Senior PM Lead at Microsoft Research,

told VentureBeat

. "Having a UI, like Microsoft Research's Magentic-UI, is vital for giving users opportunities to intervene when necessary, while also helping to avoid approval fatigue."

That matters because OpenAI was not subtle about the risks when it launched ChatGPT Agent. "When you sign ChatGPT agent into websites or enable connectors, it will be able to access sensitive data from those sources, such as emails, files, or account information," the company

wrote

.

Fara1.5 runs everything through MagenticLite, a sandboxed browser environment that logs every action and lets users halt the agent at any point.

Browser AI has become a crowded race

—Google's Gemini in Chrome, Perplexity's Comet, Anthropic's Claude for Chrome. Fara1.5's edge is that it is open: public weights, open inference code on

GitHub

, runs on hardware you control. Fara1.5-9B is live now on

Azure AI Foundry

; the 4B and 27B variants arrive shortly. Microsoft says it plans to expand Fara1.5 beyond the browser and into desktop and enterprise software next.

Daily Debrief

Newsletter

Start every day with the top news stories right now, plus original features, a podcast, videos and more.

Your Email

Get it!

Get it!
</details>
