"""
Visual + functional test for humanize.
Virtual SVG cursor follows Playwright API moves (show_cursor=True).
"""
import pytest
pytestmark = pytest.mark.slow

if __name__ == "__main__":
    from hexium_browser import launch
    import time

    def step(name):
        print(f"\n{'='*60}")
        print(f"  STEP: {name}")
        print(f"{'='*60}")

    def check(name, passed, detail=""):
        status = "PASS" if passed else "FAIL"
        msg = f"  [{status}] {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)
        results.append((name, status))

    print("=" * 70)
    print("  HUMAN-LIKE BEHAVIOR VISUAL TEST")
    print("  Virtual Hexium SVG cursor — driven by Playwright API only")
    print("  Do not move your physical mouse; watch the SVG pointer")
    print("=" * 70)

    results = []

    browser = launch(
        headless=False,
        humanize=True,
        show_cursor=True,
    )
    page = browser.new_page()

    # ============================================================
    # SCENARIO 1: Wikipedia search
    # ============================================================
    step("Wikipedia — navigate and search")
    page.goto('https://www.wikipedia.org', wait_until='domcontentloaded')
    time.sleep(2)
    time.sleep(0.3)
    time.sleep(1)

    print("  Watch: cursor moves to search box (Bezier curve)")
    t0 = time.time()
    page.locator('#searchInput').click()
    click_ms = int((time.time() - t0) * 1000)
    check("click on search input", click_ms > 200, f"{click_ms} ms")
    time.sleep(0.5)

    print("  Watch: characters appear one by one with varying speed")
    t0 = time.time()
    page.locator('#searchInput').fill('Python programming language')
    fill_ms = int((time.time() - t0) * 1000)
    val = page.locator('#searchInput').input_value()
    check("fill search box", val == 'Python programming language' and fill_ms > 2000, f"{fill_ms} ms, value='{val}'")
    time.sleep(0.5)

    print("  Watch: cursor moves to search box, double yellow flash, word selected")
    t0 = time.time()
    page.locator('#searchInput').dblclick()
    dbl_ms = int((time.time() - t0) * 1000)
    sel = page.evaluate('() => window.getSelection().toString().trim()')
    check("dblclick selects word", len(sel) > 0 and dbl_ms > 200, f"{dbl_ms} ms, selected='{sel}'")
    time.sleep(0.5)

    print("  Watch: old text cleared, new text typed")
    t0 = time.time()
    page.locator('#searchInput').fill('Artificial intelligence')
    fill2_ms = int((time.time() - t0) * 1000)
    val2 = page.locator('#searchInput').input_value()
    check("fill replaces text", val2 == 'Artificial intelligence' and fill2_ms > 1500, f"{fill2_ms} ms, value='{val2}'")
    time.sleep(0.5)

    print("  Watch: cursor moves to button without clicking")
    t0 = time.time()
    page.locator('button[type="submit"]').hover()
    hover_ms = int((time.time() - t0) * 1000)
    check("hover search button", hover_ms > 100, f"{hover_ms} ms")
    time.sleep(1)

    # ============================================================
    # SCENARIO 2: Form interaction — checkboxes
    # ============================================================
    step("Checkboxes — check and uncheck")
    page.goto('https://the-internet.herokuapp.com/checkboxes', wait_until='domcontentloaded')
    time.sleep(2)
    time.sleep(0.3)
    time.sleep(1)

    cb1 = page.locator('input[type="checkbox"]').nth(0)
    cb2 = page.locator('input[type="checkbox"]').nth(1)

    print("  Watch: cursor moves to first checkbox, clicks")
    if cb1.is_checked():
        cb1.uncheck()
        time.sleep(0.5)

    t0 = time.time()
    cb1.check()
    check_ms = int((time.time() - t0) * 1000)
    check("check checkbox 1", cb1.is_checked() and check_ms > 200, f"{check_ms} ms, checked={cb1.is_checked()}")
    time.sleep(0.5)

    print("  Watch: cursor moves to second checkbox, clicks to uncheck")
    if not cb2.is_checked():
        cb2.check()
        time.sleep(0.5)

    t0 = time.time()
    cb2.uncheck()
    uncheck_ms = int((time.time() - t0) * 1000)
    check("uncheck checkbox 2", not cb2.is_checked() and uncheck_ms > 200, f"{uncheck_ms} ms, checked={cb2.is_checked()}")
    time.sleep(1)

    # ============================================================
    # SCENARIO 3: Dropdown
    # ============================================================
    step("Dropdown — select option")
    page.goto('https://the-internet.herokuapp.com/dropdown', wait_until='domcontentloaded')
    time.sleep(2)
    time.sleep(0.3)
    time.sleep(1)

    print("  Watch: cursor moves to dropdown, hovers, option selected")
    t0 = time.time()
    page.locator('#dropdown').select_option('1')
    sel_ms = int((time.time() - t0) * 1000)
    val = page.locator('#dropdown').input_value()
    check("select option 1", val == '1' and sel_ms > 100, f"{sel_ms} ms, value='{val}'")
    time.sleep(0.5)

    t0 = time.time()
    page.locator('#dropdown').select_option('2')
    sel2_ms = int((time.time() - t0) * 1000)
    val2 = page.locator('#dropdown').input_value()
    check("select option 2", val2 == '2' and sel2_ms > 100, f"{sel2_ms} ms, value='{val2}'")
    time.sleep(1)

    # ============================================================
    # SCENARIO 4: Drag and drop
    # ============================================================
    step("Drag and Drop — move column A to B")
    page.goto('https://the-internet.herokuapp.com/drag_and_drop', wait_until='domcontentloaded')
    time.sleep(2)
    time.sleep(0.3)
    time.sleep(1)

    before_a = page.locator('#column-a header').text_content().strip()
    before_b = page.locator('#column-b header').text_content().strip()
    print(f"  Before: A='{before_a}', B='{before_b}'")

    print("  Watch: cursor moves to A, turns yellow (held), moves to B, releases")
    t0 = time.time()
    page.locator('#column-a').drag_to(page.locator('#column-b'))
    drag_ms = int((time.time() - t0) * 1000)
    time.sleep(1)

    after_a = page.locator('#column-a header').text_content().strip()
    after_b = page.locator('#column-b header').text_content().strip()
    swapped = before_a != after_a
    print(f"  After:  A='{after_a}', B='{after_b}'")
    check("drag A to B", swapped and drag_ms > 300, f"{drag_ms} ms, swapped={swapped}")
    time.sleep(1)

    # ============================================================
    # SCENARIO 5: Text editing
    # ============================================================
    step("Text editing — type, press keys, clear")
    page.goto('https://www.wikipedia.org', wait_until='domcontentloaded')
    time.sleep(2)
    time.sleep(0.3)
    time.sleep(1)

    print("  Watch: cursor clicks input, types character by character")
    t0 = time.time()
    page.locator('#searchInput').type('Hello World')
    type_ms = int((time.time() - t0) * 1000)
    val = page.locator('#searchInput').input_value()
    check("type 'Hello World'", val == 'Hello World' and type_ms > 1000, f"{type_ms} ms, value='{val}'")
    time.sleep(0.5)

    print("  Watch: cursor clicks, presses single key")
    t0 = time.time()
    page.locator('#searchInput').press('End')
    page.locator('#searchInput').press('!')
    press_ms = int((time.time() - t0) * 1000)
    val = page.locator('#searchInput').input_value()
    check("press '!' at end", '!' in val and press_ms > 100, f"{press_ms} ms, value='{val}'")
    time.sleep(0.5)

    print("  Watch: field gets cleared (Ctrl+A, Backspace)")
    t0 = time.time()
    page.locator('#searchInput').clear()
    clear_ms = int((time.time() - t0) * 1000)
    val = page.locator('#searchInput').input_value()
    check("clear field", val == '' and clear_ms > 100, f"{clear_ms} ms, value='{repr(val)}'")
    time.sleep(0.5)

    print("  Watch: press_sequentially types each key individually")
    t0 = time.time()
    page.locator('#searchInput').press_sequentially('Sequential')
    pseq_ms = int((time.time() - t0) * 1000)
    val = page.locator('#searchInput').input_value()
    check("press_sequentially", val == 'Sequential' and pseq_ms > 500, f"{pseq_ms} ms, value='{val}'")
    time.sleep(1)

    # ============================================================
    # SCENARIO 6: Mouse precision
    # ============================================================
    step("Mouse precision — move to coordinates")
    print("  Watch: cursor moves in a Bezier curve to (600, 400)")
    t0 = time.time()
    page.mouse.move(600, 400)
    move_ms = int((time.time() - t0) * 1000)
    check("mouse.move to (600,400)", move_ms > 100, f"{move_ms} ms")
    time.sleep(0.5)

    print("  Watch: cursor moves to (200, 200), clicks")
    t0 = time.time()
    page.mouse.click(200, 200)
    mclick_ms = int((time.time() - t0) * 1000)
    check("mouse.click at (200,200)", mclick_ms > 100, f"{mclick_ms} ms")
    time.sleep(0.5)

    print("  Watch: keyboard types directly (no click needed)")
    page.locator('#searchInput').click()
    time.sleep(0.3)
    t0 = time.time()
    page.keyboard.type('Direct keyboard')
    kb_ms = int((time.time() - t0) * 1000)
    check("keyboard.type", kb_ms > 500, f"{kb_ms} ms")
    time.sleep(1)

    # ============================================================
    # SCENARIO 7: ElementHandle — query_selector interactions
    # ============================================================
    step("ElementHandle — query_selector click, type, fill, hover")
    page.goto('https://www.wikipedia.org', wait_until='domcontentloaded')
    time.sleep(2)
    time.sleep(0.3)
    time.sleep(1)

    print("  Watch: get element via query_selector, cursor moves smoothly")
    el = page.query_selector('#searchInput')
    assert el is not None, "query_selector returned None"
    assert getattr(el, '_human_patched', False), "ElementHandle not patched!"

    t0 = time.time()
    el.click()
    eh_click_ms = int((time.time() - t0) * 1000)
    check("ElementHandle click", eh_click_ms > 100, f"{eh_click_ms} ms")
    time.sleep(0.5)

    print("  Watch: ElementHandle type — characters appear one by one")
    t0 = time.time()
    el.type('ElementHandle typing')
    eh_type_ms = int((time.time() - t0) * 1000)
    val = page.locator('#searchInput').input_value()
    check("ElementHandle type", val == 'ElementHandle typing' and eh_type_ms > 1500, f"{eh_type_ms} ms, value='{val}'")
    time.sleep(0.5)

    print("  Watch: ElementHandle fill — clears then types")
    t0 = time.time()
    el.fill('Filled via EH')
    eh_fill_ms = int((time.time() - t0) * 1000)
    val = page.locator('#searchInput').input_value()
    check("ElementHandle fill", val == 'Filled via EH' and eh_fill_ms > 1000, f"{eh_fill_ms} ms, value='{val}'")
    time.sleep(0.5)

    print("  Watch: ElementHandle hover — cursor moves without clicking")
    btn_el = page.query_selector('button[type="submit"]')
    t0 = time.time()
    btn_el.hover()
    eh_hover_ms = int((time.time() - t0) * 1000)
    check("ElementHandle hover", eh_hover_ms > 50, f"{eh_hover_ms} ms")
    time.sleep(0.5)

    print("  Watch: query_selector_all returns patched handles")
    page.goto('https://the-internet.herokuapp.com/checkboxes', wait_until='domcontentloaded')
    time.sleep(2)
    time.sleep(0.3)
    time.sleep(1)
    els = page.query_selector_all('input[type="checkbox"]')
    all_patched = all(getattr(e, '_human_patched', False) for e in els)
    check("query_selector_all all patched", all_patched and len(els) >= 2, f"{len(els)} elements, all_patched={all_patched}")

    if els:
        print("  Watch: click checkbox via ElementHandle")
        t0 = time.time()
        els[0].click()
        cb_click_ms = int((time.time() - t0) * 1000)
        check("ElementHandle checkbox click", cb_click_ms > 100, f"{cb_click_ms} ms")
    time.sleep(1)

    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    passed = sum(1 for _, s in results if s == "PASS")
    failed = sum(1 for _, s in results if s == "FAIL")
    total = len(results)

    for name, status in results:
        icon = "OK" if status == "PASS" else "XX"
        print(f"  [{icon}] {name}")

    print(f"\n  {passed}/{total} passed, {failed} failed")
    if failed == 0:
        print("  *** ALL TESTS PASSED ***")
    print("=" * 70)

    input("\nPress Enter to close browser...")
    browser.close()
