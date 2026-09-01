# Transition Ledger Mirror Handoff

Repository: `StegVerse-org/stegverse-gsl`

Every durable transition owned here is recorded first in this repository ledger. Repo replay/reconstruction must terminate without org/ecosystem replay.

Contract: `.stegverse/transition-ledger/contract.json`  
Emitter: `.stegverse/transition-ledger/emit.py`  
Durable root: `$XDG_STATE_HOME/stegverse/repo-ledgers/StegVerse-org/stegverse-gsl`

Receipts are append-only/hash-linked. Only evidence needed for organization reconstruction propagates to `StegVerse-org/.github`. Recording grants no authority.
