/**
 * @file interactive_mode.c
 * @brief Interactive blackjack game with strategy advisor - 5 functions
 *
 * Lets the player compete against the dealer while the system
 * watches every card and whispers what basic strategy says to do,
 * the running/true count, the recommended bet, and why.
 *
 * Author: Claudia Maria Lopez Bombin
 * License: MIT
 */

#include "../include/interactive_mode.h"
#include "../include/game_core.h"
#include "../include/hand_utils.h"
#include "../include/shoe_utils.h"
#include "../include/card_utils.h"
#include "../include/counting_system.h"
#include "../include/betting_strategy.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

/* ── internal helpers ──────────────────────────────────────────────────── */

/**
 * print_hand: Show all cards in a hand plus its best value.
 */
static void print_hand(const char* label, const Hand* hand, bool hide_hole) {
    printf("  %-8s ", label);
    for (int i = 0; i < hand->num_cards; i++) {
        if (i == 1 && hide_hole) { printf("[??] "); continue; }

        const Card* c = &hand->cards[i];
        const char* suit_sym[] = {"♥","♦","♣","♠"};
        const char* rank_sym[] = {"A","2","3","4","5","6","7","8","9","10","J","Q","K"};
        printf("[%s%s] ", rank_sym[c->rank - 1], suit_sym[c->suit]);
    }
    if (!hide_hole)
        printf("= %d%s", hand_best_value(hand),
               hand_is_soft(hand) ? " (soft)" : "");
    printf("\n");
}

/**
 * advisor_hint: Look up and print the strategy recommendation.
 *
 * Explains both WHAT to do and WHY, including count context.
 */
static void advisor_hint(const Hand* player, const Card* dealer_up,
                         const StrategyEntry* table, int num_entries,
                         int running_count, double true_count) {
    StrategyKey key;
    key.player_value  = hand_best_value(player);
    key.dealer_upcard = dealer_up->value;
    key.is_soft       = hand_is_soft(player);
    key.is_pair       = (player->num_cards == 2 &&
                         player->cards[0].rank == player->cards[1].rank);

    PlayerAction best = ACTION_STAND;
    double best_ev    = -999.0;
    bool found        = false;

    for (int i = 0; i < num_entries; i++) {
        if (table[i].key.player_value  == key.player_value  &&
            table[i].key.dealer_upcard == key.dealer_upcard &&
            table[i].key.is_soft       == key.is_soft       &&
            table[i].key.is_pair       == key.is_pair) {
            best    = table[i].action;
            best_ev = table[i].expected_value;
            found   = true;
            break;
        }
    }

    const char* action_name[] = {"HIT", "STAND", "DOUBLE", "SPLIT"};
    const char* action_desc[] = {
        "Pide carta — tu total necesita mejorar.",
        "Planta — riesgo de pasarte supera la ganancia.",
        "Dobla la apuesta — las matematicas te favorecen.",
        "Divide en dos manos — juegas mejor por separado."
    };

    printf("\n  ╔═══════════════════════════════════════╗\n");
    printf(  "  ║  🃏 ADVISOR                           ║\n");
    printf(  "  ╠═══════════════════════════════════════╣\n");

    if (found) {
        printf("  ║  Recomendación: %-22s ║\n", action_name[best]);
        printf("  ║  %-37s ║\n", action_desc[best]);
        printf("  ╠═══════════════════════════════════════╣\n");
        printf("  ║  RC: %-3d  TC: %+5.1f  EV: %+.3f      ║\n",
               running_count, true_count, best_ev);
    } else {
        printf("  ║  Sin datos — recomienda: STAND        ║\n");
        printf("  ╠═══════════════════════════════════════╣\n");
        printf("  ║  RC: %-3d  TC: %+5.1f                  ║\n",
               running_count, true_count);
    }

    /* Count interpretation */
    const char* adv = count_get_advantage_level(true_count);
    printf("  ║  Situación: %-26s ║\n", adv);
    printf("  ╚═══════════════════════════════════════╝\n\n");
}

/**
 * ask_action: Read and validate the player's chosen action.
 *
 * Keeps asking until a legal key is pressed.
 */
static PlayerAction ask_action(const Hand* hand) {
    int count;
    PlayerAction* available = game_get_available_actions(hand, &count);

    printf("  Acciones disponibles: ");
    for (int i = 0; i < count; i++) {
        const char* labels[] = {"[H]it", "[S]tand", "[D]ouble", "[P]split"};
        printf("%s  ", labels[available[i]]);
    }
    printf("\n  Tu decisión: ");

    char line[16];
    while (1) {
        if (!fgets(line, sizeof(line), stdin)) return ACTION_STAND;
        char ch = (char)toupper((unsigned char)line[0]);

        bool valid = false;
        for (int i = 0; i < count; i++) {
            if ((ch == 'H' && available[i] == ACTION_HIT)    ||
                (ch == 'S' && available[i] == ACTION_STAND)  ||
                (ch == 'D' && available[i] == ACTION_DOUBLE) ||
                (ch == 'P' && available[i] == ACTION_SPLIT)) {
                return available[i];
            }
            valid = true; (void)valid;
        }
        printf("  Tecla no válida. Intenta de nuevo: ");
    }
}

/* ── public API ─────────────────────────────────────────────────────────── */

/**
 * play_interactive_round: Play one full round with advisor active.
 *
 * Returns net profit/loss and updates running_count in place.
 */
double play_interactive_round(Shoe* shoe, double bet,
                              const StrategyEntry* table, int num_entries,
                              int* running_count) {
    Hand player, dealer;
    game_deal_initial(&player, &dealer, shoe);
    player.bet = bet;

    /* Count initial cards */
    for (int i = 0; i < player.num_cards; i++)
        count_update(running_count, &player.cards[i]);
    for (int i = 0; i < dealer.num_cards; i++)
        count_update(running_count, &dealer.cards[i]);

    double tc = count_calculate_true(*running_count, shoe);

    printf("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
    print_hand("Dealer:", &dealer, true);
    print_hand("Tú:",     &player, false);

    /* Early blackjack check */
    if (player.status == HAND_BLACKJACK) {
        printf("\n  🎉 ¡BLACKJACK! Pagas 3:2\n");
        game_play_dealer(&dealer, shoe, true);
        print_hand("Dealer:", &dealer, false);
        double result = game_calculate_payout(&player, &dealer);
        printf("  Resultado: %+.2f€\n", result);
        return result;
    }

    /* Player turn */
    while (player.status == HAND_ACTIVE) {
        tc = count_calculate_true(*running_count, shoe);
        advisor_hint(&player, &dealer.cards[0], table, num_entries,
                     *running_count, tc);

        PlayerAction action = ask_action(&player);
        game_execute_action(&player, action, shoe);

        if (player.num_cards > 0) {
            const Card* last = &player.cards[player.num_cards - 1];
            count_update(running_count, last);
        }

        if (player.status == HAND_BUST) {
            printf("\n  💥 ¡Te has pasado! (%d)\n", hand_best_value(&player));
            break;
        }
        if (action != ACTION_HIT)
            print_hand("Tú:", &player, false);
    }

    /* Dealer turn */
    printf("\n  — Turno del dealer —\n");
    game_play_dealer(&dealer, shoe, true);

    /* Count dealer's extra cards */
    for (int i = 2; i < dealer.num_cards; i++)
        count_update(running_count, &dealer.cards[i]);

    print_hand("Dealer:", &dealer, false);
    print_hand("Tú:",     &player, false);

    double result = game_calculate_payout(&player, &dealer);

    if (result > 0)       printf("\n  ✅ Ganas %+.2f€\n", result);
    else if (result < 0)  printf("\n  ❌ Pierdes %.2f€\n", -result);
    else                  printf("\n  🤝 Empate\n");

    return result;
}

/**
 * run_interactive_game: Main game loop — plays until el jugador sale.
 *
 * Loads or builds a strategy table, then loops round after round,
 * tracking bankroll and showing running stats.
 */
void run_interactive_game(const StrategyEntry* table, int num_entries) {
    bet_init(10.0, 200.0);

    Shoe shoe;
    shoe_init(&shoe, 6, 0.75);
    int running_count = 0;

    double bankroll = 500.0;
    int hands_played = 0, hands_won = 0;

    printf("\n╔══════════════════════════════════════════╗\n");
    printf(  "║   BLACKJACK — MODO INTERACTIVO           ║\n");
    printf(  "║   El advisor usa estrategia básica MC    ║\n");
    printf(  "║   Hi-Lo activo • Banca inicial: 500€     ║\n");
    printf(  "╚══════════════════════════════════════════╝\n");

    while (bankroll > 0.0) {
        if (shoe_needs_reshuffle(&shoe)) {
            printf("\n  ♻️  Barajando el mazo...\n");
            shoe_shuffle(&shoe);
            running_count = 0;
        }

        double tc = count_calculate_true(running_count, &shoe);
        double suggested_bet = bet_calculate(tc);
        if (suggested_bet > bankroll) suggested_bet = bankroll;

        printf("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
        printf("  Banca: %.2f€  |  RC: %d  TC: %+.1f\n",
               bankroll, running_count, tc);
        printf("  Apuesta recomendada: %.2f€  (%s)\n",
               suggested_bet, count_get_advantage_level(tc));
        printf("  Tu apuesta (Enter = aceptar recomendada, 'q' = salir): ");

        char line[32];
        if (!fgets(line, sizeof(line), stdin)) break;
        if (line[0] == 'q' || line[0] == 'Q') break;

        double bet = suggested_bet;
        if (line[0] != '\n') {
            double input = atof(line);
            if (input > 0 && input <= bankroll) bet = input;
        }
        if (bet <= 0) bet = 10.0;

        double result = play_interactive_round(&shoe, bet, table,
                                               num_entries, &running_count);
        bankroll += result;
        hands_played++;
        if (result > 0) hands_won++;
    }

    printf("\n╔══════════════════════════════════════════╗\n");
    printf(  "║   RESUMEN DE SESIÓN                      ║\n");
    printf(  "╠══════════════════════════════════════════╣\n");
    printf(  "║  Manos jugadas : %-24d║\n", hands_played);
    if (hands_played > 0)
        printf("║  Win rate      : %-23.1f%%║\n",
               100.0 * hands_won / hands_played);
    printf(  "║  Banca final   : %-23.2f€║\n", bankroll);
    printf(  "╚══════════════════════════════════════════╝\n\n");
}
