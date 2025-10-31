"""
Simple verification that wrapper is in the call chain.

This checks the code statically without running the full server.
"""

import sys
from pathlib import Path

print("\n" + "=" * 80)
print("🔍 AGENT LIGHTNING WRAPPER VERIFICATION")
print("=" * 80 + "\n")

verification_steps = []

# Step 1: Check chat.py uses LangGraph service
print("Step 1: Checking chat endpoint...")
try:
    chat_path = Path("app/routers/chat.py")
    with open(chat_path) as f:
        chat_content = f.read()

    if "agent_service=Depends(get_langgraph_agent_service)" in chat_content:
        print("✅ chat.py uses get_langgraph_agent_service() dependency")
        verification_steps.append(True)
    else:
        print("❌ chat.py does NOT use LangGraph service!")
        verification_steps.append(False)
except Exception as e:
    print(f"❌ Error reading chat.py: {e}")
    verification_steps.append(False)

# Step 2: Check LangGraph service wraps the agent
print("\nStep 2: Checking LangGraph service wraps agent...")
try:
    service_path = Path("app/services/langgraph_agent_service.py")
    with open(service_path) as f:
        service_content = f.read()

    checks = [
        (
            "Defines _wrap_with_agent_lightning method",
            "_wrap_with_agent_lightning" in service_content,
        ),
        (
            "Calls wrapper in __init__",
            "self.graph = self._wrap_with_agent_lightning(self.graph)" in service_content,
        ),
        ("Uses self.graph.ainvoke", "await self.graph.ainvoke(" in service_content),
        (
            "Imports agent_wrapper_service",
            "from app.services.agent_wrapper_service import wrap" in service_content,
        ),
    ]

    all_passed = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")
        if not passed:
            all_passed = False

    verification_steps.append(all_passed)

except Exception as e:
    print(f"❌ Error reading langgraph_agent_service.py: {e}")
    verification_steps.append(False)

# Step 3: Check wrapper implements ainvoke with logging
print("\nStep 3: Checking AgentWrapper implementation...")
try:
    wrapper_path = Path("app/services/agent_wrapper_service.py")
    with open(wrapper_path) as f:
        wrapper_content = f.read()

    checks = [
        ("AgentWrapper class exists", "class AgentWrapper:" in wrapper_content),
        ("ainvoke method exists", "async def ainvoke(self" in wrapper_content),
        ("Logging marker present", "AGENT_LIGHTNING_WRAPPER_INVOKED" in wrapper_content),
        ("Calls _agent.ainvoke", "await self._agent.ainvoke(query)" in wrapper_content),
    ]

    all_passed = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")
        if not passed:
            all_passed = False

    verification_steps.append(all_passed)

except Exception as e:
    print(f"❌ Error reading agent_wrapper_service.py: {e}")
    verification_steps.append(False)

# Step 4: Check config enables Agent Lightning
print("\nStep 4: Checking Agent Lightning configuration...")
try:
    config_path = Path("app/core/agent_lightning_config.py")
    with open(config_path) as f:
        config_content = f.read()

    checks = [
        ("Config module exists", True),
        ("create_optimization_config exists", "def create_optimization_config(" in config_content),
        (
            "is_agent_lightning_available exists",
            "def is_agent_lightning_available(" in config_content,
        ),
        ("Settings class exists", "class AgentLightningSettings" in config_content),
    ]

    all_passed = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")
        if not passed:
            all_passed = False

    verification_steps.append(all_passed)

except Exception as e:
    print(f"❌ Error reading agent_lightning_config.py: {e}")
    verification_steps.append(False)

# Summary
print("\n" + "=" * 80)
print("📊 VERIFICATION RESULTS")
print("=" * 80 + "\n")

passed_count = sum(verification_steps)
total_count = len(verification_steps)

if passed_count == total_count:
    print(f"✅ ALL CHECKS PASSED ({passed_count}/{total_count})")
    print()
    print("🎯 CONCLUSION: Agent Lightning wrapper IS in the call chain!")
    print()
    print("📋 Call Flow:")
    print("   Client Request")
    print("   ↓")
    print("   POST /api/v1/chat/ask")
    print("   ↓")
    print("   chat.py:ask_question()")
    print("   ↓")
    print("   agent_service.process_message()  ← Uses LangGraphAgentService")
    print("   ↓")
    print("   self.graph.ainvoke()  ← self.graph is wrapped in __init__")
    print("   ↓")
    print("   AgentWrapper.ainvoke()  ← Wrapper intercepts here! 🎯")
    print("   ↓")
    print("   self._agent.ainvoke()  ← Original LangGraph agent")
    print()
    print("✅ To verify in runtime:")
    print("   1. Start server: cd api && uv run uvicorn app.main:app --reload")
    print("   2. Send chat request: POST /api/v1/chat/ask")
    print("   3. Check logs for: '🚀 AGENT_LIGHTNING_WRAPPER_INVOKED'")
    print()
    sys.exit(0)
else:
    print(f"❌ SOME CHECKS FAILED ({passed_count}/{total_count})")
    print()
    print("⚠️  CONCLUSION: Wrapper integration may have issues!")
    print()
    sys.exit(1)
