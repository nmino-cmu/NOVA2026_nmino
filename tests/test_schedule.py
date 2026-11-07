from ghost.engine.schedule import choose, claim_exact, partition, relevance


def _item(creation, relevance_class, g, h=0, restore=0):
    return {
        "id": f"c{creation}",
        "creation": creation,
        "relevance": relevance_class,
        "g": g,
        "h": h,
        "actionCost": 1,
        "restore": restore,
        "tokens": 0,
        "status": "ready",
    }


def test_relevance_matches_task_words_and_leaves_unknowns():
    text = "Reach checkout with exactly one Nova Mug. Do not place an order."
    assert relevance("Express Nova Mug", text) == 0
    assert relevance("Catalog", text) == 1
    assert relevance("More", text) == 1


def test_every_fifth_choice_is_the_oldest():
    ready = [_item(3, 0, 1), _item(1, 2, 4), _item(2, 0, 0)]
    picked, kind = choose(ready, 4)
    assert kind == "fairness"
    assert picked["creation"] == 1


def test_low_relevance_stays_eligible_and_cheaper_arrivals_beat_exclusion():
    incumbent = 5
    ready, excluded = partition([_item(1, 2, 0), _item(2, 0, 4, h=2), _item(3, 0, 2, h=0)], incumbent)
    assert {item["creation"] for item in ready} == {1, 3}
    assert [item["creation"] for item in excluded] == [2]
    picked, kind = choose(ready, 0)
    assert kind == "heuristic"
    assert picked["creation"] == 3


def test_clearing_the_incumbent_reactivates_an_exclusion():
    item = _item(1, 0, 4)
    _, excluded = partition([item], 4)
    assert excluded
    ready, excluded = partition([item], None)
    assert ready and not excluded


def test_exact_work_is_not_dispatched_twice():
    seen: set[str] = set()
    assert claim_exact(seen, "Catalog|Nova Mug")
    assert claim_exact(seen, "Catalog|Nova Mug") is False
    assert claim_exact(seen, "Catalog|View cart")


def test_exclusion_shrinks_the_ready_set():
    items = [_item(index, 1, index) for index in range(1, 9)]
    ready, excluded = partition(items, 4)
    assert len(ready) == 3
    assert len(excluded) == 5
    assert len(ready) + len(excluded) == len(items)
