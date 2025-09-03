package common

import (
	"encoding/binary"
	"fmt"
	"io"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/op/go-logging"
)

var log = logging.MustGetLogger("log")

// Clients Bet
type Bet struct {
	Name    string
	Surname string
	Dni     uint32
	Birth   string
	Number  uint32
}

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID            string
	Agency        int
	ServerAddress string
	LoopAmount    int
	LoopPeriod    time.Duration
	BatchAmount   int
}

// Client Entity that encapsulates how
type Client struct {
	config ClientConfig
	conn   net.Conn
}

// NewClient Initializes a new client receiving the configuration
// as a parameter
func NewClient(config ClientConfig) *Client {
	client := &Client{
		config: config,
	}
	return client
}

// CreateClientSocket Initializes client socket. In case of
// failure, error is printed in stdout/stderr and exit 1
// is returned
func (c *Client) createClientSocket() error {
	conn, err := net.Dial("tcp", c.config.ServerAddress)
	if err != nil {
		log.Criticalf(
			"action: connect | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
	}
	c.conn = conn
	return nil
}

func (c *Client) MakeBets(bets []Bet, more_bets bool) {
	signalChan := make(chan os.Signal, 1)
	signal.Notify(signalChan, syscall.SIGTERM)

	select {
	case <-signalChan:
		log.Infof("action: client_stop | result: success | client_id: %v", c.config.ID)
		return
	default:
		c.createClientSocket()

		if err := c.sendBets(bets, more_bets); err != nil {
			log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
				c.config.ID,
				err,
			)
			return
		}

		if more_bets {
			last_bet_number := bets[len(bets)-1].Number
			if err := c.readResponse(last_bet_number); err != nil {
				log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
					c.config.ID,
					err,
				)
				return
			}
		} else {
			if err := c.readwinners(); err != nil {
				log.Errorf("action: receive_winners | result: fail | client_id: %v | error: %v",
					c.config.ID,
					err,
				)
				return
			}
		}

		log.Infof("action: send_batch | result: success | batch_size: %d", len(bets))
	}
}

func (c *Client) sendBets(bets []Bet, more_bets bool) error {
	msg, msg_len := EncodeBetsBatch(bets, uint8(c.config.Agency), more_bets)

	for sent := 0; sent < int(msg_len); {
		n, err := c.conn.Write(msg[sent:])
		if err != nil {
			return err
		}
		sent += n
	}

	return nil
}

func (c *Client) readResponse(expected uint32) error {
	msg := make([]byte, NUMBER_SIZE)
	if _, err := io.ReadFull(c.conn, msg); err != nil {
		return err
	}
	if err := c.conn.Close(); err != nil {
		return err
	}

	log.Infof("action: receive_message | result: success | client_id: %v | message: %s",
		c.config.ID,
		msg,
	)

	if receivedNumber := binary.BigEndian.Uint32(msg); receivedNumber != expected {
		return fmt.Errorf("received number: %d, expected: %d",
			receivedNumber,
			expected,
		)
	}

	return nil
}

func (c *Client) readwinners() error {
	winners_count := make([]byte, 2)
	if _, err := io.ReadFull(c.conn, winners_count); err != nil {
		return err
	}

	for i := uint16(0); i < binary.BigEndian.Uint16(winners_count); i++ {
		winner := make([]byte, NUMBER_SIZE)
		if _, err := io.ReadFull(c.conn, winner); err != nil {
			return err
		}
		log.Infof("action: receive_winner | result: success | client_id: %v | winner: %d",
			c.config.ID,
			binary.BigEndian.Uint32(winner),
		)
	}

	if err := c.conn.Close(); err != nil {
		return err
	}

	return nil
}
