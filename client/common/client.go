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
	ServerAddress string
	LoopAmount    int
	LoopPeriod    time.Duration
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

func (c *Client) MakeBet(bet Bet) {
	signalChan := make(chan os.Signal, 1)
	signal.Notify(signalChan, syscall.SIGTERM)

	select {
	case <-signalChan:
		log.Infof("action: client_stop | result: success | client_id: %v", c.config.ID)
		return
	default:
		c.createClientSocket()

		if err := c.sendBet(bet); err != nil {
			log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
				c.config.ID,
				err,
			)
			return
		}

		if err := c.readResponse(bet); err != nil {
			log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
				c.config.ID,
				err,
			)
			return
		}
	}
}

func (c *Client) sendBet(bet Bet) error {
	msg, msg_len := EncodeBet(bet)

	for sent := 0; sent < int(msg_len); {
		n, err := c.conn.Write(msg[sent:])
		if err != nil {
			return err
		}
		sent += n
	}

	return nil
}

func (c *Client) readResponse(bet Bet) error {
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

	if receivedNumber := binary.BigEndian.Uint32(msg); receivedNumber != bet.Number {
		return fmt.Errorf("received number: %d, expected: %d",
			receivedNumber,
			bet.Number,
		)
	}

	log.Infof("action: apuesta_enviada | result: success | dni: %v | numero: %v",
		bet.Dni,
		bet.Number,
	)

	return nil
}
