"""Tests for text processing utilities."""

from utils.text_processing import (
    calculate_word_timings,
    clean_text,
    estimate_speech_duration,
    get_text_statistics,
    split_into_sentences,
    split_into_words,
)


class TestSplitIntoSentences:
    """Tests for split_into_sentences function."""

    def test_empty_string(self):
        """Test with empty string."""
        assert split_into_sentences("") == []

    def test_whitespace_only(self):
        """Test with whitespace only."""
        assert split_into_sentences("   \n\t  ") == []

    def test_single_sentence_english(self):
        """Test single English sentence."""
        text = "Hello world."
        result = split_into_sentences(text)
        assert len(result) == 1
        assert result[0] == "Hello world."

    def test_single_sentence_russian(self):
        """Test single Russian sentence."""
        text = "Привет мир."
        result = split_into_sentences(text)
        assert len(result) == 1
        assert result[0] == "Привет мир."

    def test_multiple_sentences_english(self):
        """Test multiple English sentences."""
        text = "First sentence. Second sentence! Third sentence?"
        result = split_into_sentences(text)
        assert len(result) == 3
        assert result[0] == "First sentence"
        assert result[1] == "Second sentence"
        assert result[2] == "Third sentence?"

    def test_multiple_sentences_russian(self):
        """Test multiple Russian sentences."""
        text = "Первое предложение. Второе предложение! Третье предложение?"
        result = split_into_sentences(text)
        assert len(result) == 3
        assert "Первое" in result[0]
        assert "Второе" in result[1]
        assert "Третье" in result[2]

    def test_mixed_languages(self):
        """Test text with mixed Russian and English."""
        text = "Hello world. Привет мир. Goodbye."
        result = split_into_sentences(text)
        assert len(result) == 3

    def test_ellipsis(self):
        """Test sentence splitting with ellipsis."""
        text = "Wait... What happened? I don't know!"
        result = split_into_sentences(text)
        assert len(result) >= 2

    def test_no_trailing_punctuation(self):
        """Test text without trailing punctuation."""
        text = "This is a sentence without end"
        result = split_into_sentences(text)
        assert len(result) == 1
        assert result[0] == text


class TestSplitIntoWords:
    """Tests for split_into_words function."""

    def test_empty_string(self):
        """Test with empty string."""
        assert split_into_words("") == []

    def test_simple_sentence(self):
        """Test simple sentence."""
        text = "Hello world"
        result = split_into_words(text)
        assert result == ["Hello", "world"]

    def test_with_punctuation(self):
        """Test sentence with punctuation."""
        text = "Hello, world! How are you?"
        result = split_into_words(text)
        assert result == ["Hello", "world", "How", "are", "you"]

    def test_russian_text(self):
        """Test Russian text."""
        text = "Привет мир как дела"
        result = split_into_words(text)
        assert len(result) == 4
        assert "Привет" in result

    def test_numbers(self):
        """Test text with numbers."""
        text = "I have 2 apples and 3 oranges"
        result = split_into_words(text)
        assert "2" in result
        assert "3" in result
        assert len(result) == 7


class TestCalculateWordTimings:
    """Tests for calculate_word_timings function."""

    def test_empty_sentence(self):
        """Test with empty sentence."""
        assert calculate_word_timings("", 1.0) == []

    def test_single_word(self):
        """Test with single word."""
        result = calculate_word_timings("Hello", 1.0)
        assert len(result) == 1
        word, start, end = result[0]
        assert word == "Hello"
        assert start == 0.0
        assert abs(end - 1.0) < 0.01

    def test_multiple_words(self):
        """Test with multiple words."""
        result = calculate_word_timings("Hi there friend", 3.0)
        assert len(result) == 3

        # Check that timings are sequential
        for i in range(len(result) - 1):
            _, _, end_current = result[i]
            _, start_next, _ = result[i + 1]
            assert abs(end_current - start_next) < 0.01

        # Last word should end at approximately 3.0
        _, _, last_end = result[-1]
        assert abs(last_end - 3.0) < 0.1

    def test_timing_proportional_to_length(self):
        """Test that longer words get more time."""
        result = calculate_word_timings("I am extraordinary", 2.0)
        assert len(result) == 3

        _, short_start, short_end = result[0]  # "I"
        _, long_start, long_end = result[2]  # "extraordinary"

        short_duration = short_end - short_start
        long_duration = long_end - long_start

        # Longer word should have more time
        assert long_duration > short_duration


class TestCleanText:
    """Tests for clean_text function."""

    def test_empty_string(self):
        """Test with empty string."""
        assert clean_text("") == ""

    def test_excessive_whitespace(self):
        """Test removal of excessive whitespace."""
        text = "Hello    world\n\nwith\t\ttabs"
        result = clean_text(text)
        assert "  " not in result
        assert "\n" not in result
        assert "\t" not in result

    def test_control_characters(self):
        """Test removal of control characters."""
        text = "Hello\x00world\x0btest"
        result = clean_text(text)
        assert "\x00" not in result
        assert "\x0b" not in result
        assert "Helloworld test" == result

    def test_quote_normalization(self):
        """Test quote normalization."""
        text = '«Hello» „world" test'
        result = clean_text(text)
        assert "«" not in result
        assert "»" not in result
        assert "„" not in result

    def test_strip(self):
        """Test that text is stripped."""
        text = "  Hello world  \n"
        assert clean_text(text) == "Hello world"


class TestEstimateSpeechDuration:
    """Tests for estimate_speech_duration function."""

    def test_empty_string(self):
        """Test with empty string."""
        assert estimate_speech_duration("") == 0.0

    def test_single_word(self):
        """Test with single word."""
        duration = estimate_speech_duration("Hello")
        assert duration > 0

    def test_known_duration(self):
        """Test with known word count."""
        # 150 words per minute = 2.5 words per second
        # 10 words should take approximately 4 seconds
        text = "one two three four five six seven eight nine ten"
        duration = estimate_speech_duration(text, words_per_minute=150)
        assert abs(duration - 4.0) < 0.5

    def test_custom_wpm(self):
        """Test with custom words per minute."""
        text = "one two three four five"
        # At 300 WPM (twice as fast), duration should be half
        duration_fast = estimate_speech_duration(text, words_per_minute=300)
        duration_slow = estimate_speech_duration(text, words_per_minute=150)
        assert duration_fast < duration_slow
        assert abs(duration_slow - 2 * duration_fast) < 0.1


class TestGetTextStatistics:
    """Tests for get_text_statistics function."""

    def test_empty_string(self):
        """Test with empty string."""
        stats = get_text_statistics("")
        assert stats["sentences"] == 0
        assert stats["words"] == 0
        assert stats["characters"] == 0
        assert stats["estimated_duration"] == 0.0

    def test_simple_text(self):
        """Test with simple text."""
        text = "Hello world. This is a test."
        stats = get_text_statistics(text)
        assert stats["sentences"] == 2
        assert stats["words"] == 6
        assert stats["characters"] == len(text)
        assert stats["estimated_duration"] > 0

    def test_statistics_consistency(self):
        """Test that statistics are consistent."""
        text = "First sentence. Second sentence!"
        stats = get_text_statistics(text)

        # Duration should be positive for non-empty text
        assert stats["estimated_duration"] > 0

        # Word count should match split_into_words
        assert stats["words"] == len(split_into_words(text))

        # Sentence count should match split_into_sentences
        assert stats["sentences"] == len(split_into_sentences(text))
