#!/usr/bin/env python3
import sys
import re

BE_VERBS = {'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being'}
IRREGULAR_PARTICIPLES = {
    'done', 'seen', 'taken', 'known', 'written', 'given', 'made', 'built', 
    'run', 'shown', 'held', 'kept', 'met', 'put', 'set', 'left', 'told', 
    'brought', 'caught', 'fought', 'taught', 'bought', 'thought', 'felt', 
    'found', 'lost', 'heard', 'sent', 'spent', 'paid', 'led', 'read', 
    'spoken', 'frozen', 'broken', 'chosen', 'stolen', 'forgotten', 'eaten', 
    'fallen', 'shaken', 'begun', 'sung', 'drunk', 'blown', 'grown', 'thrown',
    'drawn', 'flown', 'ridden', 'driven', 'arisen', 'striven', 'slain'
}

ABBREVIATIONS = {
    'e.g.', 'i.e.', 'mr.', 'mrs.', 'ms.', 'dr.', 'prof.', 'vs.', 'etc.', 
    'pr.', 'adr.', 'co.', 'corp.', 'inc.', 'ltd.', 'st.', 'ave.', 'rd.'
}

def count_syllables(word):
    word = word.lower().strip(".,;:?!()[]'\"-")
    if not word:
        return 0
    word = "".join(c for c in word if c.isalpha())
    if not word:
        return 0
    
    vowels = "aeiouy"
    count = 0
    is_vowel = False
    for char in word:
        if char in vowels:
            if not is_vowel:
                count += 1
                is_vowel = True
        else:
            is_vowel = False
            
    if word.endswith("e"):
        if len(word) > 2 and word[-2] == "l" and word[-3] not in vowels:
            pass
        else:
            count -= 1
            
    return max(1, count)

def is_past_participle(word):
    word = word.lower().strip(".,;:?!()[]'\"-")
    if word.endswith("ed"):
        return True
    if word in IRREGULAR_PARTICIPLES:
        return True
    return False

def check_passive(words, index):
    if words[index] not in BE_VERBS:
        return None
    for offset in range(1, 4):
        if index + offset >= len(words):
            break
        w = words[index + offset]
        if is_past_participle(w):
            phrase = " ".join(words[index : index + offset + 1])
            return phrase
        if w.endswith("ly") or w in {"not", "been", "being"}:
            continue
        break
    return None

def get_sentences(text):
    sentences = []
    current_acc = []
    
    for line in text.splitlines():
        line = line.strip()
        if not line:
            if current_acc:
                sentences.append(" ".join(current_acc))
                current_acc = []
            continue
            
        is_header = line.startswith("#")
        is_list_item = any(line.startswith(prefix) for prefix in ["- ", "* ", "+ "]) or bool(re.match(r'^\d+\.\s', line))
        
        if is_header or is_list_item:
            if current_acc:
                sentences.append(" ".join(current_acc))
                current_acc = []
            
            clean_line = line
            if is_header:
                clean_line = line.lstrip("#").strip()
            elif is_list_item:
                clean_line = re.sub(r'^(?:[-*+]+|\d+\.)\s+', '', line).strip()
            
            if clean_line:
                sentences.append(clean_line)
            continue
            
        raw_splits = re.split(r'(?<=[.!?])\s+', line)
        for s in raw_splits:
            if not s.strip():
                continue
            current_acc.append(s)
            last_word = s.split()[-1].lower().rstrip("!?") if s.split() else ""
            if last_word not in ABBREVIATIONS:
                sentences.append(" ".join(current_acc))
                current_acc = []
                
    if current_acc:
        sentences.append(" ".join(current_acc))
        
    return sentences

def analyze_text(text):
    if not text.strip():
        return None
        
    sentences = get_sentences(text)
    if not sentences:
        return None
        
    total_words = 0
    total_sentences = 0
    total_syllables = 0
    long_sentences = []
    passive_constructions = []
    passive_stacking = []
    
    for s in sentences:
        words = []
        for w in s.split():
            clean = "".join(c for c in w if c.isalnum() or c == "'")
            if clean:
                words.append(clean)
        
        word_count = len(words)
        if word_count == 0:
            continue
        total_words += word_count
        total_sentences += 1
        
        if word_count > 25:
            long_sentences.append((word_count, s))
            
        for w in words:
            total_syllables += count_syllables(w)
            
        lower_words = [w.lower() for w in words]
        sentence_passives = []
        i = 0
        while i < len(lower_words):
            phrase = check_passive(lower_words, i)
            if phrase:
                sentence_passives.append(phrase)
                passive_constructions.append((phrase, s))
                i += len(phrase.split()) - 1
            i += 1
            
        if len(sentence_passives) >= 2:
            passive_stacking.append((sentence_passives, s))
            
    if total_words == 0 or total_sentences == 0:
        return None
        
    asl = total_words / total_sentences
    asw = total_syllables / total_words
    fk_grade = 0.39 * asl + 11.8 * asw - 15.59
    
    return {
        'fk_grade': round(fk_grade, 2),
        'total_words': total_words,
        'total_sentences': total_sentences,
        'long_sentences': long_sentences,
        'passives': passive_constructions,
        'passive_stacking': passive_stacking
    }

def main():
    if len(sys.argv) > 1 and sys.argv[1] != "-":
        try:
            with open(sys.argv[1], 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        text = sys.stdin.read()
        
    results = analyze_text(text)
    if not results:
        print("Empty or tiny input. No readability metrics computed.")
        sys.exit(0)
        
    print(f"Flesch-Kincaid Grade Level: {results['fk_grade']}")
    print(f"Total Words: {results['total_words']}")
    print(f"Total Sentences: {results['total_sentences']}")
    print(f"Average Words per Sentence: {round(results['total_words'] / results['total_sentences'], 1)}")
    print()
    
    if results['long_sentences']:
        print(f"--- Long Sentences (>25 words) [{len(results['long_sentences'])} found] ---")
        for count, s in results['long_sentences']:
            print(f"({count} words): {s.strip()}")
        print()
        
    if results['passives']:
        print(f"--- Passive Voice Constructions [{len(results['passives'])} found] ---")
        for phrase, s in results['passives']:
            print(f"Passive phrase: '{phrase}' in: {s.strip()}")
        print()
        
    if results['passive_stacking']:
        print(f"--- Passive Stacking Warning (>=2 passives in one sentence) [{len(results['passive_stacking'])} found] ---")
        for phrases, s in results['passive_stacking']:
            print(f"Stacked passives: {phrases} in: {s.strip()}")
        print()

if __name__ == "__main__":
    main()
