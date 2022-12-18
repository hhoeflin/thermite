from thermite.preprocessing import split_and_expand


def test_split_and_expand():
    assert split_and_expand(["-vvf", "test", "--this", "other"]) == [
        ["-v"],
        ["-v"],
        ["-f", "test"],
        ["--this", "other"],
    ]
